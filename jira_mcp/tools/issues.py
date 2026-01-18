"""JIRA Issue Tools - CRUD and search operations."""

from typing import Any, Optional

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.utils.logging import get_logger


def format_issue(issue: dict[str, Any]) -> str:
    """Format issue data as readable markdown.

    Args:
        issue: Issue data from JIRA API

    Returns:
        Formatted markdown string
    """
    fields = issue.get("fields", {})
    key = issue.get("key", "N/A")
    summary = fields.get("summary", "N/A")
    status = fields.get("status", {}).get("name", "N/A")
    issue_type = fields.get("issuetype", {}).get("name", "N/A")
    assignee = fields.get("assignee", {}).get("displayName", "Unassigned")
    description = fields.get("description", "No description")

    # Handle Atlassian Document Format (ADF) for description
    if isinstance(description, dict):
        description = _extract_text_from_adf(description)

    output = f"""# {key}: {summary}

**Type:** {issue_type}
**Status:** {status}
**Assignee:** {assignee}

## Description
{description}
"""
    return output


def _extract_text_from_adf(adf: dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format.

    Args:
        adf: ADF document structure

    Returns:
        Extracted text
    """
    if not isinstance(adf, dict):
        return str(adf)

    text_parts = []
    content = adf.get("content", [])

    for node in content:
        if node.get("type") == "paragraph":
            para_content = node.get("content", [])
            para_text = []
            for text_node in para_content:
                if text_node.get("type") == "text":
                    para_text.append(text_node.get("text", ""))
            text_parts.append("".join(para_text))

    return "\n\n".join(text_parts) if text_parts else "No description"


def format_search_results(results: dict[str, Any]) -> str:
    """Format search results as readable markdown.

    Args:
        results: Search results from JIRA API

    Returns:
        Formatted markdown string
    """
    issues = results.get("issues", [])
    total = results.get("total", 0)
    start_at = results.get("startAt", 0)

    output = f"# Search Results\n\n**Total:** {total} issues (showing from {start_at})\n\n"

    for issue in issues:
        fields = issue.get("fields", {})
        key = issue.get("key", "N/A")
        summary = fields.get("summary", "N/A")
        status = fields.get("status", {}).get("name", "N/A")

        output += f"- **{key}**: {summary} [{status}]\n"

    return output


def register_issue_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register issue-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """
    logger = get_logger()

    @mcp.tool()
    async def jira_get_issue(
        issue_key: str,
        fields: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> str:
        """Get JIRA issue details by key.

        Retrieves detailed information about a specific JIRA issue including
        summary, description, status, assignee, and other fields.

        Args:
            issue_key: The issue key (e.g., PROJ-123)
            fields: Comma-separated list of fields to return (optional)
            expand: Comma-separated list of fields to expand (optional)

        Returns:
            Formatted issue details in markdown

        Example:
            jira_get_issue("PROJ-123")
            jira_get_issue("PROJ-123", fields="summary,status,assignee")
        """
        if not config.is_tool_enabled("jira_get_issue"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Getting issue: {issue_key}")
            fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
            expand_list = [e.strip() for e in expand.split(",") if e.strip()] if expand else None
            result = await client.get_issue(issue_key, fields_list, expand_list)
            return format_issue(result)
        except Exception as e:
            logger.error(f"Failed to get issue {issue_key}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_create_issue(
        project_key: str,
        summary: str,
        issue_type: str,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[str] = None,
    ) -> str:
        """Create a new JIRA issue.

        Creates a new issue in the specified project with the given details.

        Args:
            project_key: Project key (e.g., PROJ)
            summary: Issue summary/title
            issue_type: Issue type (e.g., Bug, Task, Story)
            description: Issue description (optional)
            assignee: Assignee account ID or email (optional)
            priority: Priority name (e.g., High, Medium, Low) (optional)
            labels: Comma-separated labels (optional)

        Returns:
            Created issue details in markdown

        Example:
            jira_create_issue("PROJ", "Fix login bug", "Bug", "Users cannot login")
            jira_create_issue("PROJ", "Add feature", "Story", labels="feature,p1")
        """
        if not config.is_tool_enabled("jira_create_issue"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot create issue - server is in read-only mode"

        try:
            logger.info(f"Creating issue in project: {project_key}")

            # Build issue data
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type},
                }
            }

            # Add optional fields
            if description:
                issue_data["fields"]["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                }

            if assignee:
                issue_data["fields"]["assignee"] = {"id": assignee}

            if priority:
                issue_data["fields"]["priority"] = {"name": priority}

            if labels:
                issue_data["fields"]["labels"] = [
                    label.strip() for label in labels.split(",")
                ]

            result = await client.create_issue(issue_data)

            # Fetch the created issue to get full details
            created_key = result.get("key")
            if created_key:
                full_issue = await client.get_issue(created_key)
                return f"✅ Issue created successfully!\n\n{format_issue(full_issue)}"
            else:
                return f"✅ Issue created: {result}"

        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_update_issue(
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[str] = None,
    ) -> str:
        """Update an existing JIRA issue.

        Updates fields of an existing issue. Only provided fields will be updated.

        Args:
            issue_key: The issue key (e.g., PROJ-123)
            summary: New summary/title (optional)
            description: New description (optional)
            assignee: New assignee account ID or email (optional)
            priority: New priority name (optional)
            labels: New comma-separated labels (optional)

        Returns:
            Updated issue details in markdown

        Example:
            jira_update_issue("PROJ-123", summary="Updated title")
            jira_update_issue("PROJ-123", priority="High", labels="urgent,bug")
        """
        if not config.is_tool_enabled("jira_update_issue"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot update issue - server is in read-only mode"

        try:
            logger.info(f"Updating issue: {issue_key}")

            # Build update data
            update_data = {"fields": {}}

            if summary:
                update_data["fields"]["summary"] = summary

            if description:
                update_data["fields"]["description"] = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                }

            if assignee:
                update_data["fields"]["assignee"] = {"id": assignee}

            if priority:
                update_data["fields"]["priority"] = {"name": priority}

            if labels:
                update_data["fields"]["labels"] = [
                    label.strip() for label in labels.split(",")
                ]

            await client.update_issue(issue_key, update_data)

            # Fetch updated issue
            updated_issue = await client.get_issue(issue_key)
            return f"✅ Issue updated successfully!\n\n{format_issue(updated_issue)}"

        except Exception as e:
            logger.error(f"Failed to update issue {issue_key}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_delete_issue(issue_key: str) -> str:
        """Delete a JIRA issue.

        Permanently deletes an issue from JIRA. This action cannot be undone.

        Args:
            issue_key: The issue key to delete (e.g., PROJ-123)

        Returns:
            Confirmation message

        Example:
            jira_delete_issue("PROJ-123")
        """
        if not config.is_tool_enabled("jira_delete_issue"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot delete issue - server is in read-only mode"

        try:
            logger.info(f"Deleting issue: {issue_key}")
            await client.delete_issue(issue_key)
            return f"✅ Issue {issue_key} deleted successfully"
        except Exception as e:
            logger.error(f"Failed to delete issue {issue_key}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_search(
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[str] = None,
    ) -> str:
        """Search JIRA issues using JQL (JIRA Query Language).

        Executes a JQL query to find issues matching specific criteria.

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return (default: 50)
            start_at: Index of first result to return (default: 0)
            fields: Comma-separated list of fields to return (optional)

        Returns:
            Search results in markdown

        Example:
            jira_search("project = PROJ AND status = 'In Progress'")
            jira_search("assignee = currentUser() AND status != Done", max_results=10)
            jira_search("labels = urgent", fields="summary,status,assignee")
        """
        if not config.is_tool_enabled("jira_search"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Searching issues with JQL: {jql}")
            fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
            result = await client.search_issues(jql, fields_list, max_results, start_at)
            return format_search_results(result)
        except Exception as e:
            logger.error(f"Failed to search issues: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_batch_create_issues(issues_json: str) -> str:
        """Bulk create multiple JIRA issues.

        Creates multiple issues in a single API call. More efficient than
        creating issues one at a time.

        Args:
            issues_json: JSON string containing array of issue objects.
                Each object should have: projectKey, summary, issueType,
                and optional description, assignee, priority, labels.

        Returns:
            Results of bulk creation in markdown

        Example:
            jira_batch_create_issues('[
                {"projectKey": "PROJ", "summary": "Bug 1", "issueType": "Bug"},
                {"projectKey": "PROJ", "summary": "Bug 2", "issueType": "Bug"}
            ]')
        """
        if not config.is_tool_enabled("jira_batch_create_issues"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot create issues - server is in read-only mode"

        try:
            import json

            logger.info("Batch creating issues")

            # Parse input JSON
            issues_data = json.loads(issues_json)

            # Build bulk request
            issues = []
            for issue_obj in issues_data:
                issue_data = {
                    "fields": {
                        "project": {"key": issue_obj["projectKey"]},
                        "summary": issue_obj["summary"],
                        "issuetype": {"name": issue_obj["issueType"]},
                    }
                }

                # Add optional fields
                if "description" in issue_obj:
                    issue_data["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": issue_obj["description"]}
                                ],
                            }
                        ],
                    }

                if "assignee" in issue_obj:
                    issue_data["fields"]["assignee"] = {"id": issue_obj["assignee"]}

                if "priority" in issue_obj:
                    issue_data["fields"]["priority"] = {"name": issue_obj["priority"]}

                if "labels" in issue_obj:
                    issue_data["fields"]["labels"] = issue_obj["labels"]

                issues.append(issue_data)

            result = await client.batch_create_issues(issues)

            # Format results
            created = result.get("issues", [])
            errors = result.get("errors", [])

            output = f"# Batch Create Results\n\n**Created:** {len(created)} issues\n**Errors:** {len(errors)}\n\n"

            if created:
                output += "## Successfully Created\n\n"
                for issue in created:
                    key = issue.get("key", "N/A")
                    output += f"- {key}\n"

            if errors:
                output += "\n## Errors\n\n"
                for error in errors:
                    output += f"- {error}\n"

            return output

        except Exception as e:
            logger.error(f"Failed to batch create issues: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_batch_get_changelogs(issue_keys: str) -> str:
        """Get changelogs for multiple issues.

        Retrieves the change history for multiple issues in a single API call.

        Args:
            issue_keys: Comma-separated list of issue keys (e.g., "PROJ-1,PROJ-2,PROJ-3")

        Returns:
            Changelogs in markdown

        Example:
            jira_batch_get_changelogs("PROJ-123,PROJ-456")
        """
        if not config.is_tool_enabled("jira_batch_get_changelogs"):
            return "Tool is disabled by configuration"

        try:
            keys_list = [key.strip() for key in issue_keys.split(",")]
            logger.info(f"Getting changelogs for {len(keys_list)} issues")

            changelogs = []
            for key in keys_list:
                try:
                    changelog_data = await client.get_issue_changelog(key)
                    changelogs.append({"issueKey": key, "changelog": changelog_data.get("changelog", {})})
                except Exception as e:
                    logger.warning(f"Failed to get changelog for {key}: {e}")

            output = "# Issue Changelogs\n\n"

            for issue_data in changelogs:
                key = issue_data.get("issueKey", "N/A")
                histories = issue_data.get("changelog", {}).get("histories", [])

                output += f"## {key}\n\n"

                if not histories:
                    output += "No changes recorded.\n\n"
                    continue

                for history in histories:
                    author = history.get("author", {}).get("displayName", "Unknown")
                    created = history.get("created", "N/A")
                    output += f"**{author}** - {created}\n\n"

                    for item in history.get("items", []):
                        field = item.get("field", "N/A")
                        from_val = item.get("fromString", "")
                        to_val = item.get("toString", "")
                        output += f"  - {field}: {from_val} → {to_val}\n"

                    output += "\n"

            return output

        except Exception as e:
            logger.error(f"Failed to get changelogs: {e}")
            return f"Error: {str(e)}"
