"""JIRA Issue Link Tools - Create and manage issue links."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_link_types(data: dict[str, Any]) -> str:
    """Format issue link types into readable markdown.

    Args:
        data: Link types data from API

    Returns:
        Formatted markdown string
    """
    link_types = data.get("issueLinkTypes", [])

    if not link_types:
        return "No issue link types found."

    lines = ["# Issue Link Types\n"]
    for link_type in link_types:
        name = link_type.get("name", "Unknown")
        inward = link_type.get("inward", "")
        outward = link_type.get("outward", "")
        link_id = link_type.get("id", "")

        lines.append(f"## {name} (ID: {link_id})")
        lines.append(f"- **Inward:** {inward}")
        lines.append(f"- **Outward:** {outward}\n")

    return "\n".join(lines)


def format_issue_link(data: dict[str, Any]) -> str:
    """Format issue link result into readable markdown.

    Args:
        data: Link data from API

    Returns:
        Formatted markdown string
    """
    if not data:
        return "Issue link created successfully."

    return f"Issue link created:\n- ID: {data.get('id', 'N/A')}"


def format_remote_link(data: dict[str, Any]) -> str:
    """Format remote link result into readable markdown.

    Args:
        data: Remote link data from API

    Returns:
        Formatted markdown string
    """
    link_id = data.get("id", "N/A")
    self_url = data.get("self", "")

    return f"""# Remote Link Created

- **ID:** {link_id}
- **URL:** {self_url}
"""


def register_link_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register issue link tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_get_link_types() -> str:
        """Get all available issue link types.

        Returns issue link types that can be used to create links between issues.
        Each type has an inward and outward description.

        Returns:
            Formatted markdown string with link types
        """
        if not config.is_tool_enabled("jira_get_link_types"):
            return "Tool is disabled by configuration"

        result = await client.get_link_types()
        return format_link_types(result)

    @mcp.tool()
    async def jira_create_issue_link(
        link_type: str,
        inward_issue: str,
        outward_issue: str,
        comment: str = "",
    ) -> str:
        """Create a link between two JIRA issues.

        Creates a directional link between two issues using the specified link type.
        The link type determines the relationship (e.g., "blocks", "relates to").

        Args:
            link_type: Type of link (e.g., "Blocks", "Relates")
            inward_issue: Issue key that is the target of the link
            outward_issue: Issue key that is the source of the link
            comment: Optional comment to add with the link

        Returns:
            Success message with link details

        Example:
            jira_create_issue_link("Blocks", "PROJ-123", "PROJ-456", "Blocking issue")
        """
        if not config.is_tool_enabled("jira_create_issue_link"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        result = await client.create_issue_link(
            link_type=link_type,
            inward_issue=inward_issue,
            outward_issue=outward_issue,
            comment=comment if comment else None,
        )
        return format_issue_link(result)

    @mcp.tool()
    async def jira_remove_issue_link(link_id: str) -> str:
        """Remove an issue link by ID.

        Deletes an existing link between two issues. The link ID can be found
        using the issue details or link types query.

        Args:
            link_id: ID of the link to remove

        Returns:
            Success message

        Example:
            jira_remove_issue_link("10001")
        """
        if not config.is_tool_enabled("jira_remove_issue_link"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        await client.remove_issue_link(link_id)
        return f"Issue link {link_id} removed successfully."

    @mcp.tool()
    async def jira_create_remote_issue_link(
        issue_key: str,
        url: str,
        title: str,
        summary: str = "",
    ) -> str:
        """Create a remote link to an external resource.

        Adds a link from a JIRA issue to an external URL (e.g., documentation,
        pull requests, external tickets).

        Args:
            issue_key: Issue key to add the link to
            url: URL of the external resource
            title: Title/label for the link
            summary: Optional description of the link

        Returns:
            Success message with link details

        Example:
            jira_create_remote_issue_link(
                "PROJ-123",
                "https://github.com/org/repo/pull/456",
                "Related PR",
                "Pull request fixing this issue"
            )
        """
        if not config.is_tool_enabled("jira_create_remote_issue_link"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        result = await client.create_remote_issue_link(
            issue_key=issue_key,
            url=url,
            title=title,
            summary=summary if summary else None,
        )
        return format_remote_link(result)
