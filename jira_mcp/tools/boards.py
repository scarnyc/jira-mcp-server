"""Board operations for JIRA Agile."""

from typing import Any, Optional

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_boards(boards: list[dict[str, Any]]) -> str:
    """Format boards list as readable markdown.

    Args:
        boards: List of board dictionaries

    Returns:
        Formatted markdown string
    """
    if not boards:
        return "No boards found."

    output = [f"# Found {len(boards)} board(s)\n"]

    for board in boards:
        output.append(f"## {board.get('name', 'Unnamed Board')}")
        output.append(f"- **ID:** {board.get('id')}")
        output.append(f"- **Type:** {board.get('type', 'N/A')}")

        if location := board.get('location'):
            project_key = location.get('projectKey', 'N/A')
            output.append(f"- **Project:** {project_key}")

        output.append("")

    return "\n".join(output)


def format_board_issues(issues: list[dict[str, Any]], board_name: str = "Board") -> str:
    """Format board issues as readable markdown.

    Args:
        issues: List of issue dictionaries
        board_name: Name of the board

    Returns:
        Formatted markdown string
    """
    if not issues:
        return f"No issues found on {board_name}."

    output = [f"# Issues on {board_name}\n"]
    output.append(f"Total: {len(issues)} issue(s)\n")
    output.append("| Key | Summary | Type | Status | Assignee |")
    output.append("|-----|---------|------|--------|----------|")

    for issue in issues:
        key = issue.get('key', 'N/A')
        fields = issue.get('fields', {})
        summary = fields.get('summary', 'N/A')
        issue_type = fields.get('issuetype', {}).get('name', 'N/A')
        status = fields.get('status', {}).get('name', 'N/A')

        assignee_data = fields.get('assignee')
        assignee = assignee_data.get('displayName', 'Unassigned') if assignee_data else 'Unassigned'

        # Escape pipe characters in values
        summary = summary.replace('|', '\\|')
        assignee = assignee.replace('|', '\\|')

        output.append(f"| {key} | {summary} | {issue_type} | {status} | {assignee} |")

    return "\n".join(output)


def register_board_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register board-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_get_agile_boards(
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
    ) -> str:
        """List agile boards in JIRA.

        Args:
            project_key: Filter boards by project key (optional)
            board_type: Filter by board type: 'scrum' or 'kanban' (optional)

        Returns:
            Formatted list of boards with their IDs, types, and projects

        Examples:
            - Get all boards: jira_get_agile_boards()
            - Get boards for project: jira_get_agile_boards(project_key="PROJ")
            - Get scrum boards: jira_get_agile_boards(board_type="scrum")
        """
        if not config.is_tool_enabled("jira_get_agile_boards"):
            return "Tool 'jira_get_agile_boards' is disabled by configuration."

        try:
            result = await client.get_agile_boards(
                project_key=project_key,
                board_type=board_type,
            )
            boards = result.get("values", []) if isinstance(result, dict) else result
            return format_boards(boards)
        except Exception as e:
            return f"Error retrieving boards: {str(e)}"

    @mcp.tool()
    async def jira_get_board_issues(
        board_id: int,
        jql: Optional[str] = None,
        max_results: int = 50,
    ) -> str:
        """Get issues from a specific agile board.

        Args:
            board_id: The board ID to retrieve issues from
            jql: Optional JQL filter to apply (e.g., "assignee = currentUser()")
            max_results: Maximum number of issues to return (default: 50, max: 100)

        Returns:
            Formatted table of issues on the board

        Examples:
            - Get all board issues: jira_get_board_issues(board_id=123)
            - Filter by assignee: jira_get_board_issues(board_id=123, jql="assignee = currentUser()")
            - Limit results: jira_get_board_issues(board_id=123, max_results=20)
        """
        if not config.is_tool_enabled("jira_get_board_issues"):
            return "Tool 'jira_get_board_issues' is disabled by configuration."

        # Validate max_results
        if max_results > 100:
            max_results = 100
        elif max_results < 1:
            max_results = 1

        try:
            result = await client.get_board_issues(
                board_id=board_id,
                jql=jql,
                max_results=max_results,
            )

            issues = result.get('issues', [])
            board_name = result.get('board_name', f"Board {board_id}")

            return format_board_issues(issues, board_name)
        except Exception as e:
            return f"Error retrieving board issues: {str(e)}"
