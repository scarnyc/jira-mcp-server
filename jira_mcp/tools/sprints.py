"""Sprint operations for JIRA Agile."""

from typing import Any, Optional

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_sprints(sprints: list[dict[str, Any]], board_id: Optional[int] = None) -> str:
    """Format sprints list as readable markdown.

    Args:
        sprints: List of sprint dictionaries
        board_id: Optional board ID for context

    Returns:
        Formatted markdown string
    """
    if not sprints:
        board_text = f" for board {board_id}" if board_id else ""
        return f"No sprints found{board_text}."

    board_text = f" for Board {board_id}" if board_id else ""
    output = [f"# Found {len(sprints)} sprint(s){board_text}\n"]

    for sprint in sprints:
        output.append(f"## {sprint.get('name', 'Unnamed Sprint')}")
        output.append(f"- **ID:** {sprint.get('id')}")
        output.append(f"- **State:** {sprint.get('state', 'N/A')}")

        if start_date := sprint.get('startDate'):
            output.append(f"- **Start Date:** {start_date}")
        if end_date := sprint.get('endDate'):
            output.append(f"- **End Date:** {end_date}")
        if goal := sprint.get('goal'):
            output.append(f"- **Goal:** {goal}")

        output.append("")

    return "\n".join(output)


def format_sprint_issues(
    issues: list[dict[str, Any]],
    sprint_name: str = "Sprint",
) -> str:
    """Format sprint issues as readable markdown.

    Args:
        issues: List of issue dictionaries
        sprint_name: Name of the sprint

    Returns:
        Formatted markdown string
    """
    if not issues:
        return f"No issues found in {sprint_name}."

    output = [f"# Issues in {sprint_name}\n"]
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


def format_sprint_created(sprint: dict[str, Any]) -> str:
    """Format created sprint information.

    Args:
        sprint: Sprint dictionary

    Returns:
        Formatted markdown string
    """
    output = [f"# Sprint Created Successfully\n"]
    output.append(f"- **Name:** {sprint.get('name')}")
    output.append(f"- **ID:** {sprint.get('id')}")
    output.append(f"- **State:** {sprint.get('state', 'N/A')}")

    if start_date := sprint.get('startDate'):
        output.append(f"- **Start Date:** {start_date}")
    if end_date := sprint.get('endDate'):
        output.append(f"- **End Date:** {end_date}")
    if goal := sprint.get('goal'):
        output.append(f"- **Goal:** {goal}")

    return "\n".join(output)


def register_sprint_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register sprint-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_get_sprints_from_board(
        board_id: int,
        state: Optional[str] = None,
    ) -> str:
        """Get all sprints from a specific board.

        Args:
            board_id: The board ID to retrieve sprints from
            state: Filter by sprint state: 'active', 'future', or 'closed' (optional)

        Returns:
            Formatted list of sprints with their IDs, states, and dates

        Examples:
            - Get all sprints: jira_get_sprints_from_board(board_id=123)
            - Get active sprints: jira_get_sprints_from_board(board_id=123, state="active")
            - Get future sprints: jira_get_sprints_from_board(board_id=123, state="future")
        """
        if not config.is_tool_enabled("jira_get_sprints_from_board"):
            return "Tool 'jira_get_sprints_from_board' is disabled by configuration."

        try:
            sprints = await client.get_sprints_from_board(
                board_id=board_id,
                state=state,
            )
            return format_sprints(sprints, board_id)
        except Exception as e:
            return f"Error retrieving sprints: {str(e)}"

    @mcp.tool()
    async def jira_get_sprint_issues(
        sprint_id: int,
        jql: Optional[str] = None,
        max_results: int = 50,
    ) -> str:
        """Get issues from a specific sprint.

        Args:
            sprint_id: The sprint ID to retrieve issues from
            jql: Optional JQL filter to apply (e.g., "assignee = currentUser()")
            max_results: Maximum number of issues to return (default: 50, max: 100)

        Returns:
            Formatted table of issues in the sprint with story points

        Examples:
            - Get all sprint issues: jira_get_sprint_issues(sprint_id=456)
            - Filter by type: jira_get_sprint_issues(sprint_id=456, jql="type = Story")
            - Limit results: jira_get_sprint_issues(sprint_id=456, max_results=20)
        """
        if not config.is_tool_enabled("jira_get_sprint_issues"):
            return "Tool 'jira_get_sprint_issues' is disabled by configuration."

        # Validate max_results
        if max_results > 100:
            max_results = 100
        elif max_results < 1:
            max_results = 1

        try:
            result = await client.get_sprint_issues(
                sprint_id=sprint_id,
                jql=jql,
                max_results=max_results,
            )

            issues = result.get('issues', [])
            sprint_name = result.get('sprint_name', f"Sprint {sprint_id}")

            return format_sprint_issues(issues, sprint_name)
        except Exception as e:
            return f"Error retrieving sprint issues: {str(e)}"

    @mcp.tool()
    async def jira_create_sprint(
        name: str,
        board_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> str:
        """Create a new sprint on a board.

        Args:
            name: Name of the sprint
            board_id: The board ID to create the sprint on
            start_date: Sprint start date in ISO format (e.g., "2025-01-01T09:00:00.000Z")
            end_date: Sprint end date in ISO format (e.g., "2025-01-14T17:00:00.000Z")
            goal: Sprint goal description (optional)

        Returns:
            Confirmation message with sprint details

        Examples:
            - Basic sprint: jira_create_sprint(name="Sprint 10", board_id=123)
            - With dates: jira_create_sprint(name="Sprint 10", board_id=123,
                start_date="2025-01-01T09:00:00.000Z", end_date="2025-01-14T17:00:00.000Z")
            - With goal: jira_create_sprint(name="Sprint 10", board_id=123, goal="Complete feature X")
        """
        if not config.is_tool_enabled("jira_create_sprint"):
            return "Tool 'jira_create_sprint' is disabled by configuration."

        if config.read_only:
            return "Cannot create sprint: Server is in read-only mode."

        try:
            sprint = await client.create_sprint(
                name=name,
                board_id=board_id,
                start_date=start_date,
                end_date=end_date,
                goal=goal,
            )
            return format_sprint_created(sprint)
        except Exception as e:
            return f"Error creating sprint: {str(e)}"

    @mcp.tool()
    async def jira_update_sprint(
        sprint_id: int,
        name: Optional[str] = None,
        state: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> str:
        """Update an existing sprint.

        Args:
            sprint_id: The sprint ID to update
            name: New sprint name (optional)
            state: New sprint state: 'active' or 'closed' (optional)
            start_date: New start date in ISO format (optional)
            end_date: New end date in ISO format (optional)
            goal: New sprint goal (optional)

        Returns:
            Confirmation message with updated sprint details

        Examples:
            - Start sprint: jira_update_sprint(sprint_id=456, state="active")
            - Close sprint: jira_update_sprint(sprint_id=456, state="closed")
            - Update name and goal: jira_update_sprint(sprint_id=456, name="Sprint 11",
                goal="Bug fixes and polish")
            - Extend dates: jira_update_sprint(sprint_id=456, end_date="2025-01-21T17:00:00.000Z")
        """
        if not config.is_tool_enabled("jira_update_sprint"):
            return "Tool 'jira_update_sprint' is disabled by configuration."

        if config.read_only:
            return "Cannot update sprint: Server is in read-only mode."

        # Validate state if provided
        if state and state not in ['active', 'closed']:
            return f"Invalid state '{state}'. Must be 'active' or 'closed'."

        try:
            sprint = await client.update_sprint(
                sprint_id=sprint_id,
                name=name,
                state=state,
                start_date=start_date,
                end_date=end_date,
                goal=goal,
            )
            return f"Sprint updated successfully.\n\n{format_sprints([sprint])}"
        except Exception as e:
            return f"Error updating sprint: {str(e)}"
