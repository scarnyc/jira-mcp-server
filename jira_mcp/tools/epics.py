"""Epic operations for JIRA Agile."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_epic_issues(issues: list[dict[str, Any]], epic_key: str) -> str:
    """Format epic issues as readable markdown.

    Args:
        issues: List of issue dictionaries
        epic_key: Key of the parent epic

    Returns:
        Formatted markdown string
    """
    if not issues:
        return f"No issues found for epic {epic_key}."

    output = [f"# Issues in Epic {epic_key}\n"]
    output.append(f"Total: {len(issues)} issue(s)\n")
    output.append("| Key | Summary | Type | Status | Assignee | Story Points |")
    output.append("|-----|---------|------|--------|----------|--------------|")

    for issue in issues:
        key = issue.get('key', 'N/A')
        fields = issue.get('fields', {})
        summary = fields.get('summary', 'N/A')
        issue_type = fields.get('issuetype', {}).get('name', 'N/A')
        status = fields.get('status', {}).get('name', 'N/A')

        assignee_data = fields.get('assignee')
        assignee = assignee_data.get('displayName', 'Unassigned') if assignee_data else 'Unassigned'

        # Story points can be in different custom fields
        story_points = fields.get('customfield_10016') or fields.get('storyPoints', 'N/A')
        if story_points and not isinstance(story_points, str):
            story_points = str(story_points)

        # Escape pipe characters
        summary = summary.replace('|', '\\|')
        assignee = assignee.replace('|', '\\|')

        output.append(f"| {key} | {summary} | {issue_type} | {status} | {assignee} | {story_points} |")

    return "\n".join(output)


def register_epic_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register epic-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_link_to_epic(
        issue_key: str,
        epic_key: str,
    ) -> str:
        """Link an issue to an epic.

        This creates a parent-child relationship where the epic is the parent
        and the issue becomes a child of that epic.

        Args:
            issue_key: The issue key to link (e.g., "PROJ-123")
            epic_key: The epic key to link to (e.g., "PROJ-100")

        Returns:
            Confirmation message

        Examples:
            - Link story to epic: jira_link_to_epic(issue_key="PROJ-123", epic_key="PROJ-100")
            - Link task to epic: jira_link_to_epic(issue_key="PROJ-456", epic_key="PROJ-100")
        """
        if not config.is_tool_enabled("jira_link_to_epic"):
            return "Tool 'jira_link_to_epic' is disabled by configuration."

        if config.read_only:
            return "Cannot link issue to epic: Server is in read-only mode."

        try:
            await client.link_to_epic(
                issue_key=issue_key,
                epic_key=epic_key,
            )
            return f"Successfully linked {issue_key} to epic {epic_key}."
        except Exception as e:
            return f"Error linking issue to epic: {str(e)}"

    @mcp.tool()
    async def jira_get_epic_issues(
        epic_key: str,
        max_results: int = 50,
    ) -> str:
        """Get all issues that belong to an epic.

        Args:
            epic_key: The epic key to retrieve issues from (e.g., "PROJ-100")
            max_results: Maximum number of issues to return (default: 50, max: 100)

        Returns:
            Formatted table of issues in the epic with story points

        Examples:
            - Get all epic issues: jira_get_epic_issues(epic_key="PROJ-100")
            - Limit results: jira_get_epic_issues(epic_key="PROJ-100", max_results=20)
        """
        if not config.is_tool_enabled("jira_get_epic_issues"):
            return "Tool 'jira_get_epic_issues' is disabled by configuration."

        # Validate max_results
        if max_results > 100:
            max_results = 100
        elif max_results < 1:
            max_results = 1

        try:
            issues = await client.get_epic_issues(
                epic_key=epic_key,
                max_results=max_results,
            )
            return format_epic_issues(issues, epic_key)
        except Exception as e:
            return f"Error retrieving epic issues: {str(e)}"
