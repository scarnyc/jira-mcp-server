"""JIRA Worklog Tools - Track time spent on issues."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_worklog_entry(data: dict[str, Any]) -> str:
    """Format worklog entry into readable markdown.

    Args:
        data: Worklog data from API

    Returns:
        Formatted markdown string
    """
    worklog_id = data.get("id", "N/A")
    time_spent = data.get("timeSpent", "N/A")
    started = data.get("started", "N/A")
    author = data.get("author", {}).get("displayName", "Unknown")
    comment = data.get("comment", "No comment")

    return f"""# Worklog Entry Created

- **ID:** {worklog_id}
- **Time Spent:** {time_spent}
- **Started:** {started}
- **Author:** {author}
- **Comment:** {comment}
"""


def format_worklogs(data: dict[str, Any]) -> str:
    """Format worklog list into readable markdown.

    Args:
        data: Worklogs data from API

    Returns:
        Formatted markdown string
    """
    worklogs = data.get("worklogs", [])

    if not worklogs:
        return "No worklogs found for this issue."

    lines = ["# Worklogs\n"]
    total_seconds = 0

    for worklog in worklogs:
        author = worklog.get("author", {}).get("displayName", "Unknown")
        time_spent = worklog.get("timeSpent", "N/A")
        time_seconds = worklog.get("timeSpentSeconds", 0)
        started = worklog.get("started", "N/A")
        comment = worklog.get("comment", "No comment")

        total_seconds += time_seconds

        lines.append(f"## {author} - {time_spent}")
        lines.append(f"- **Started:** {started}")
        lines.append(f"- **Comment:** {comment}\n")

    # Calculate total time
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    total_time = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

    lines.insert(1, f"**Total Time Logged:** {total_time}\n")

    return "\n".join(lines)


def register_worklog_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register worklog tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_add_worklog(
        issue_key: str,
        time_spent: str,
        comment: str = "",
        started: str = "",
    ) -> str:
        """Log time spent on a JIRA issue.

        Adds a worklog entry to track time spent working on an issue.
        Time can be specified in various formats (e.g., "3h 30m", "1d 2h", "45m").

        Args:
            issue_key: Issue key to log time against
            time_spent: Time spent (e.g., "3h 30m", "1d", "45m")
            comment: Optional description of work performed
            started: Optional start time in ISO 8601 format (e.g., "2024-01-15T09:00:00.000+0000")

        Returns:
            Formatted worklog entry details

        Examples:
            jira_add_worklog("PROJ-123", "2h 30m", "Implemented new feature")
            jira_add_worklog("PROJ-456", "1d", "Code review and testing")
        """
        if not config.is_tool_enabled("jira_add_worklog"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        result = await client.add_worklog(
            issue_key=issue_key,
            time_spent=time_spent,
            comment=comment if comment else None,
            started=started if started else None,
        )
        return format_worklog_entry(result)

    @mcp.tool()
    async def jira_get_worklog(issue_key: str) -> str:
        """Get all worklog entries for a JIRA issue.

        Retrieves all time tracking entries logged against an issue, including
        who logged time, when, and how much.

        Args:
            issue_key: Issue key to get worklogs for

        Returns:
            Formatted list of worklog entries with total time

        Example:
            jira_get_worklog("PROJ-123")
        """
        if not config.is_tool_enabled("jira_get_worklog"):
            return "Tool is disabled by configuration"

        result = await client.get_worklog(issue_key)
        return format_worklogs(result)
