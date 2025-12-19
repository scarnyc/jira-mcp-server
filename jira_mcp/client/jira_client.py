"""JIRA API client with async HTTP requests and retry logic."""

import asyncio
from pathlib import Path
from typing import Any, Optional

import httpx

from jira_mcp.config import JiraConfig
from jira_mcp.utils.auth import get_auth_headers
from jira_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class JiraAPIError(Exception):
    """Base exception for JIRA API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class JiraAuthenticationError(JiraAPIError):
    """Authentication failed."""

    pass


class JiraNotFoundError(JiraAPIError):
    """Resource not found (404)."""

    pass


class JiraPermissionError(JiraAPIError):
    """Permission denied (403)."""

    pass


class JiraValidationError(JiraAPIError):
    """Validation error (400)."""

    pass


class JiraRateLimitError(JiraAPIError):
    """Rate limit exceeded (429)."""

    pass


class JiraClient:
    """Async JIRA API client with retry logic and comprehensive endpoint support.

    Supports both Basic Auth (Atlassian Cloud) and Personal Access Token
    (JIRA Server/Data Center) authentication.
    """

    def __init__(self, config: JiraConfig):
        """Initialize JIRA client.

        Args:
            config: JIRA configuration object
        """
        self.config = config
        self.base_url = config.url
        self.headers = get_auth_headers(config)
        self.timeout = httpx.Timeout(config.timeout)

        # Create async client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            verify=config.verify_ssl,
        )

        logger.info(
            f"Initialized JIRA client for {self.base_url} "
            f"(Cloud: {config.is_cloud}, PAT: {config.use_pat})"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("JIRA client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        files: Optional[dict] = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            files: Files to upload
            retry_count: Current retry attempt

        Returns:
            Response JSON data

        Raises:
            JiraAPIError: If request fails after retries
        """
        # Handle different endpoint formats:
        # - Full URLs (http/https) - use as-is
        # - Full REST paths (/rest/...) - use as-is (for Agile API, etc.)
        # - Relative paths (/issues/...) - prepend REST API v2 base
        if endpoint.startswith("http"):
            url = endpoint
        elif endpoint.startswith("/rest/"):
            url = endpoint
        else:
            url = f"/rest/api/2{endpoint}"

        try:
            logger.debug(f"{method} {url} (attempt {retry_count + 1})")

            # Prepare request kwargs
            kwargs: dict[str, Any] = {"params": params}

            if files:
                # For file uploads, don't send JSON content-type
                headers = {k: v for k, v in self.headers.items() if k != "Content-Type"}
                kwargs["headers"] = headers
                kwargs["files"] = files
                if json_data:
                    kwargs["data"] = json_data
            elif json_data:
                kwargs["json"] = json_data

            response = await self.client.request(method, url, **kwargs)

            # Handle different status codes
            if response.status_code == 200:
                return response.json() if response.content else {}
            elif response.status_code == 201:
                return response.json() if response.content else {}
            elif response.status_code == 204:
                return {}  # No content
            elif response.status_code == 401:
                raise JiraAuthenticationError(
                    "Authentication failed. Check credentials.",
                    status_code=401,
                    response_data=self._safe_json(response),
                )
            elif response.status_code == 403:
                raise JiraPermissionError(
                    "Permission denied. Check user permissions.",
                    status_code=403,
                    response_data=self._safe_json(response),
                )
            elif response.status_code == 404:
                raise JiraNotFoundError(
                    f"Resource not found: {url}",
                    status_code=404,
                    response_data=self._safe_json(response),
                )
            elif response.status_code == 400:
                error_data = self._safe_json(response)
                error_msg = self._extract_error_message(error_data)
                raise JiraValidationError(
                    f"Validation error: {error_msg}",
                    status_code=400,
                    response_data=error_data,
                )
            elif response.status_code == 429:
                # Rate limit - retry with backoff
                if retry_count < self.config.max_retries:
                    await self._backoff(retry_count)
                    return await self._request(
                        method, endpoint, params, json_data, files, retry_count + 1
                    )
                raise JiraRateLimitError(
                    "Rate limit exceeded",
                    status_code=429,
                    response_data=self._safe_json(response),
                )
            elif response.status_code >= 500:
                # Server error - retry with backoff
                if retry_count < self.config.max_retries:
                    await self._backoff(retry_count)
                    return await self._request(
                        method, endpoint, params, json_data, files, retry_count + 1
                    )
                raise JiraAPIError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=self._safe_json(response),
                )
            else:
                raise JiraAPIError(
                    f"Unexpected status code: {response.status_code}",
                    status_code=response.status_code,
                    response_data=self._safe_json(response),
                )

        except httpx.TimeoutException as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Request timeout, retrying... ({retry_count + 1})")
                await self._backoff(retry_count)
                return await self._request(
                    method, endpoint, params, json_data, files, retry_count + 1
                )
            raise JiraAPIError(f"Request timeout after {retry_count + 1} attempts") from e

        except httpx.NetworkError as e:
            if retry_count < self.config.max_retries:
                logger.warning(f"Network error, retrying... ({retry_count + 1})")
                await self._backoff(retry_count)
                return await self._request(
                    method, endpoint, params, json_data, files, retry_count + 1
                )
            raise JiraAPIError(f"Network error after {retry_count + 1} attempts") from e

    @staticmethod
    def _safe_json(response: httpx.Response) -> Optional[dict]:
        """Safely extract JSON from response."""
        try:
            return response.json()
        except Exception:
            return None

    @staticmethod
    def _extract_error_message(error_data: Optional[dict]) -> str:
        """Extract error message from JIRA error response."""
        if not error_data:
            return "Unknown error"

        # Try different error message formats
        if "errorMessages" in error_data and error_data["errorMessages"]:
            return ", ".join(error_data["errorMessages"])
        elif "errors" in error_data and error_data["errors"]:
            errors = error_data["errors"]
            return ", ".join(f"{k}: {v}" for k, v in errors.items())
        elif "message" in error_data:
            return error_data["message"]
        else:
            return str(error_data)

    @staticmethod
    async def _backoff(retry_count: int) -> None:
        """Exponential backoff delay."""
        delay = min(2**retry_count, 30)  # Max 30 seconds
        logger.debug(f"Backing off for {delay} seconds")
        await asyncio.sleep(delay)

    # ================== Issue Operations ==================

    async def get_issue(
        self,
        key: str,
        fields: Optional[list[str]] = None,
        expand: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Get issue details.

        Args:
            key: Issue key (e.g., PROJ-123)
            fields: List of fields to include
            expand: List of entities to expand

        Returns:
            Issue data
        """
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        if expand:
            params["expand"] = ",".join(expand)

        return await self._request("GET", f"/issue/{key}", params=params)

    async def create_issue(
        self,
        project: str,
        issue_type: str,
        summary: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new issue.

        Args:
            project: Project key or ID
            issue_type: Issue type name or ID
            summary: Issue summary
            **kwargs: Additional fields (description, assignee, priority, etc.)

        Returns:
            Created issue data
        """
        fields: dict[str, Any] = {
            "project": {"key": project} if isinstance(project, str) else {"id": project},
            "issuetype": {"name": issue_type} if isinstance(issue_type, str) else {"id": issue_type},
            "summary": summary,
        }

        # Add optional fields
        if "description" in kwargs:
            fields["description"] = kwargs["description"]
        if "assignee" in kwargs:
            fields["assignee"] = {"name": kwargs["assignee"]}
        if "priority" in kwargs:
            fields["priority"] = {"name": kwargs["priority"]}
        if "labels" in kwargs:
            fields["labels"] = kwargs["labels"]
        if "components" in kwargs:
            fields["components"] = [{"name": c} for c in kwargs["components"]]
        if "parent" in kwargs:
            fields["parent"] = {"key": kwargs["parent"]}

        # Add any custom fields
        for key, value in kwargs.items():
            if key not in ["description", "assignee", "priority", "labels", "components", "parent"]:
                fields[key] = value

        return await self._request("POST", "/issue", json_data={"fields": fields})

    async def update_issue(
        self,
        key: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """Update issue fields.

        Args:
            key: Issue key
            fields: Fields to update

        Returns:
            Empty response on success
        """
        return await self._request("PUT", f"/issue/{key}", json_data={"fields": fields})

    async def delete_issue(self, key: str) -> dict[str, Any]:
        """Delete an issue.

        Args:
            key: Issue key

        Returns:
            Empty response on success
        """
        return await self._request("DELETE", f"/issue/{key}")

    async def search_issues(
        self,
        jql: str,
        fields: Optional[list[str]] = None,
        max_results: int = 50,
        start_at: int = 0,
    ) -> dict[str, Any]:
        """Search issues with JQL.

        Args:
            jql: JQL query string
            fields: Fields to include in results
            max_results: Maximum results to return
            start_at: Starting index for pagination

        Returns:
            Search results with issues
        """
        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at,
        }

        # Cloud API v3 requires explicit fields (new search/jql endpoint doesn't return them by default)
        if self.config.is_cloud:
            default_fields = [
                "summary", "status", "priority", "issuetype", "assignee",
                "reporter", "created", "updated", "description", "labels",
                "components", "project", "resolution", "resolutiondate"
            ]
            params["fields"] = ",".join(fields if fields else default_fields)
        elif fields:
            params["fields"] = ",".join(fields)

        # Use new search/jql endpoint for Cloud (old endpoints deprecated - 410)
        # See: https://developer.atlassian.com/changelog/#CHANGE-2046
        endpoint = "/rest/api/3/search/jql" if self.config.is_cloud else "/search"
        return await self._request("GET", endpoint, params=params)

    async def batch_create_issues(
        self,
        issues: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create multiple issues in one request.

        Args:
            issues: List of issue data (each with fields dict)

        Returns:
            Batch creation results
        """
        return await self._request("POST", "/issue/bulk", json_data={"issueUpdates": issues})

    async def get_issue_changelog(self, key: str) -> dict[str, Any]:
        """Get issue changelog (history).

        Args:
            key: Issue key

        Returns:
            Changelog data
        """
        return await self._request("GET", f"/issue/{key}?expand=changelog")

    # ================== Comment Operations ==================

    async def add_comment(self, key: str, body: str) -> dict[str, Any]:
        """Add comment to issue.

        Args:
            key: Issue key
            body: Comment text

        Returns:
            Created comment data
        """
        return await self._request(
            "POST",
            f"/issue/{key}/comment",
            json_data={"body": body},
        )

    async def get_comments(self, key: str) -> dict[str, Any]:
        """Get all comments for an issue.

        Args:
            key: Issue key

        Returns:
            Comments data
        """
        return await self._request("GET", f"/issue/{key}/comment")

    # ================== Transition Operations ==================

    async def get_transitions(self, key: str) -> dict[str, Any]:
        """Get available transitions for issue.

        Args:
            key: Issue key

        Returns:
            Available transitions
        """
        return await self._request("GET", f"/issue/{key}/transitions")

    async def transition_issue(
        self,
        key: str,
        transition_id: str,
        fields: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Transition issue to new status.

        Args:
            key: Issue key
            transition_id: Transition ID
            fields: Optional fields to update during transition

        Returns:
            Empty response on success
        """
        data: dict[str, Any] = {"transition": {"id": transition_id}}
        if fields:
            data["fields"] = fields

        return await self._request("POST", f"/issue/{key}/transitions", json_data=data)

    # ================== Project Operations ==================

    async def get_all_projects(self) -> list[dict[str, Any]]:
        """Get all accessible projects.

        Returns:
            List of projects
        """
        result = await self._request("GET", "/project")
        return result if isinstance(result, list) else []

    async def get_project_issues(
        self,
        project_key: str,
        jql_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get all issues for a project.

        Args:
            project_key: Project key
            jql_filter: Optional additional JQL filter

        Returns:
            Search results
        """
        jql = f"project = {project_key}"
        if jql_filter:
            jql += f" AND {jql_filter}"

        return await self.search_issues(jql, max_results=100)

    # ================== Agile/Board Operations ==================

    async def get_agile_boards(
        self,
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get agile boards.

        Args:
            project_key: Filter by project key
            board_type: Filter by board type (scrum, kanban)

        Returns:
            Boards data
        """
        params = {}
        if project_key:
            params["projectKeyOrId"] = project_key
        if board_type:
            params["type"] = board_type

        # Agile API uses different base path
        endpoint = "/rest/agile/1.0/board"
        return await self._request("GET", endpoint, params=params)

    async def get_board_issues(self, board_id: int) -> dict[str, Any]:
        """Get issues on a board.

        Args:
            board_id: Board ID

        Returns:
            Issues data
        """
        endpoint = f"/rest/agile/1.0/board/{board_id}/issue"
        return await self._request("GET", endpoint)

    async def get_sprints(
        self,
        board_id: int,
        state: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get sprints for a board.

        Args:
            board_id: Board ID
            state: Sprint state filter (active, future, closed)

        Returns:
            Sprints data
        """
        params = {}
        if state:
            params["state"] = state

        endpoint = f"/rest/agile/1.0/board/{board_id}/sprint"
        return await self._request("GET", endpoint, params=params)

    async def get_sprint_issues(self, sprint_id: int) -> dict[str, Any]:
        """Get issues in a sprint.

        Args:
            sprint_id: Sprint ID

        Returns:
            Issues data
        """
        endpoint = f"/rest/agile/1.0/sprint/{sprint_id}/issue"
        return await self._request("GET", endpoint)

    async def create_sprint(
        self,
        board_id: int,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new sprint.

        Args:
            board_id: Board ID
            name: Sprint name
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date

        Returns:
            Created sprint data
        """
        data: dict[str, Any] = {
            "name": name,
            "originBoardId": board_id,
        }
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date

        endpoint = "/rest/agile/1.0/sprint"
        return await self._request("POST", endpoint, json_data=data)

    async def update_sprint(
        self,
        sprint_id: int,
        **kwargs,
    ) -> dict[str, Any]:
        """Update sprint details.

        Args:
            sprint_id: Sprint ID
            **kwargs: Fields to update (name, state, startDate, endDate)

        Returns:
            Updated sprint data
        """
        endpoint = f"/rest/agile/1.0/sprint/{sprint_id}"
        return await self._request("PUT", endpoint, json_data=kwargs)

    # ================== Epic Operations ==================

    async def link_issue_to_epic(
        self,
        issue_key: str,
        epic_key: str,
    ) -> dict[str, Any]:
        """Link an issue to an epic.

        Args:
            issue_key: Issue key to link
            epic_key: Epic key

        Returns:
            Empty response on success
        """
        # Use epic link field
        return await self.update_issue(issue_key, {"customfield_10014": epic_key})

    async def get_epic_issues(self, epic_key: str) -> dict[str, Any]:
        """Get all issues in an epic.

        Args:
            epic_key: Epic key

        Returns:
            Search results
        """
        jql = f'"Epic Link" = {epic_key}'
        return await self.search_issues(jql, max_results=100)

    # ================== Issue Link Operations ==================

    async def get_link_types(self) -> list[dict[str, Any]]:
        """Get all issue link types.

        Returns:
            List of link types
        """
        result = await self._request("GET", "/issueLinkType")
        return result.get("issueLinkTypes", []) if isinstance(result, dict) else []

    async def create_issue_link(
        self,
        link_type: str,
        inward_key: str,
        outward_key: str,
    ) -> dict[str, Any]:
        """Create link between two issues.

        Args:
            link_type: Link type name
            inward_key: Inward issue key
            outward_key: Outward issue key

        Returns:
            Empty response on success
        """
        data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_key},
            "outwardIssue": {"key": outward_key},
        }
        return await self._request("POST", "/issueLink", json_data=data)

    async def remove_issue_link(self, link_id: str) -> dict[str, Any]:
        """Remove issue link.

        Args:
            link_id: Link ID

        Returns:
            Empty response on success
        """
        return await self._request("DELETE", f"/issueLink/{link_id}")

    async def create_remote_link(
        self,
        key: str,
        url: str,
        title: str,
    ) -> dict[str, Any]:
        """Create remote link (external URL) for issue.

        Args:
            key: Issue key
            url: Remote URL
            title: Link title

        Returns:
            Created link data
        """
        data = {
            "object": {
                "url": url,
                "title": title,
            }
        }
        return await self._request("POST", f"/issue/{key}/remotelink", json_data=data)

    # ================== Worklog Operations ==================

    async def add_worklog(
        self,
        key: str,
        time_spent: str,
        started: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        """Add work log entry.

        Args:
            key: Issue key
            time_spent: Time spent (e.g., "3h 30m")
            started: ISO 8601 start time
            comment: Worklog comment

        Returns:
            Created worklog data
        """
        data: dict[str, Any] = {"timeSpent": time_spent}
        if started:
            data["started"] = started
        if comment:
            data["comment"] = comment

        return await self._request("POST", f"/issue/{key}/worklog", json_data=data)

    async def get_worklogs(self, key: str) -> dict[str, Any]:
        """Get all worklogs for issue.

        Args:
            key: Issue key

        Returns:
            Worklogs data
        """
        return await self._request("GET", f"/issue/{key}/worklog")

    # ================== Version Operations ==================

    async def get_project_versions(self, project_key: str) -> list[dict[str, Any]]:
        """Get all versions for project.

        Args:
            project_key: Project key

        Returns:
            List of versions
        """
        result = await self._request("GET", f"/project/{project_key}/versions")
        return result if isinstance(result, list) else []

    async def create_version(
        self,
        project_key: str,
        name: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Create project version.

        Args:
            project_key: Project key
            name: Version name
            **kwargs: Optional fields (description, releaseDate, released, archived)

        Returns:
            Created version data
        """
        data: dict[str, Any] = {
            "name": name,
            "project": project_key,
        }
        data.update(kwargs)

        return await self._request("POST", "/version", json_data=data)

    # ================== Attachment Operations ==================

    async def download_attachment(self, attachment_id: str) -> bytes:
        """Download attachment content.

        Args:
            attachment_id: Attachment ID

        Returns:
            Attachment bytes
        """
        endpoint = f"/attachment/content/{attachment_id}"
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.content

    async def add_attachment(
        self,
        key: str,
        file_path: str,
        filename: Optional[str] = None,
    ) -> dict[str, Any]:
        """Add attachment to issue.

        Args:
            key: Issue key
            file_path: Path to file
            filename: Optional custom filename

        Returns:
            Created attachment data
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = filename or path.name

        with open(path, "rb") as f:
            files = {"file": (file_name, f, "application/octet-stream")}
            # Attachment endpoint needs special headers
            headers = {
                "X-Atlassian-Token": "no-check",
                "Accept": "application/json",
            }
            if "Authorization" in self.headers:
                headers["Authorization"] = self.headers["Authorization"]

            endpoint = f"/rest/api/2/issue/{key}/attachments"

            response = await self.client.post(
                endpoint,
                files=files,
                headers=headers,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise JiraAPIError(
                    f"Failed to upload attachment: {response.status_code}",
                    status_code=response.status_code,
                    response_data=self._safe_json(response),
                )

    # ================== User Operations ==================

    async def get_current_user(self) -> dict[str, Any]:
        """Get current authenticated user.

        Returns:
            User data
        """
        endpoint = "/myself"
        return await self._request("GET", endpoint)

    async def get_user(self, account_id: str) -> dict[str, Any]:
        """Get user by account ID.

        Args:
            account_id: User account ID

        Returns:
            User data
        """
        params = {"accountId": account_id}
        return await self._request("GET", "/user", params=params)

    async def search_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users.

        Args:
            query: Search query

        Returns:
            List of matching users
        """
        params = {"query": query}
        result = await self._request("GET", "/user/search", params=params)
        return result if isinstance(result, list) else []

    # ================== Field Operations ==================

    async def get_fields(self) -> list[dict[str, Any]]:
        """Get all available fields.

        Returns:
            List of field definitions
        """
        result = await self._request("GET", "/field")
        return result if isinstance(result, list) else []
