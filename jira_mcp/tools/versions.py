"""JIRA Version Tools - Manage project versions and releases."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_versions(data: dict[str, Any]) -> str:
    """Format versions list into readable markdown.

    Args:
        data: Versions data from API

    Returns:
        Formatted markdown string
    """
    versions = data if isinstance(data, list) else data.get("versions", [])

    if not versions:
        return "No versions found for this project."

    lines = ["# Project Versions\n"]

    for version in versions:
        name = version.get("name", "Unknown")
        version_id = version.get("id", "N/A")
        description = version.get("description", "No description")
        released = "✓ Released" if version.get("released", False) else "Not released"
        archived = "✓ Archived" if version.get("archived", False) else "Active"
        release_date = version.get("releaseDate", "Not set")
        start_date = version.get("startDate", "Not set")

        lines.append(f"## {name}")
        lines.append(f"- **ID:** {version_id}")
        lines.append(f"- **Status:** {released} | {archived}")
        lines.append(f"- **Description:** {description}")
        lines.append(f"- **Start Date:** {start_date}")
        lines.append(f"- **Release Date:** {release_date}\n")

    return "\n".join(lines)


def format_version_created(data: dict[str, Any]) -> str:
    """Format created version into readable markdown.

    Args:
        data: Version data from API

    Returns:
        Formatted markdown string
    """
    name = data.get("name", "Unknown")
    version_id = data.get("id", "N/A")
    self_url = data.get("self", "")

    return f"""# Version Created

- **Name:** {name}
- **ID:** {version_id}
- **URL:** {self_url}
"""


def format_batch_versions(data: dict[str, Any]) -> str:
    """Format batch created versions into readable markdown.

    Args:
        data: Batch versions data

    Returns:
        Formatted markdown string
    """
    versions = data.get("versions", [])

    if not versions:
        return "No versions were created."

    lines = [f"# {len(versions)} Versions Created\n"]

    for version in versions:
        name = version.get("name", "Unknown")
        version_id = version.get("id", "N/A")
        lines.append(f"- **{name}** (ID: {version_id})")

    return "\n".join(lines)


def register_version_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register version tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_get_project_versions(project_key: str) -> str:
        """Get all versions for a JIRA project.

        Lists all versions (releases) defined for a project, including their
        release status, dates, and descriptions.

        Args:
            project_key: Project key (e.g., "PROJ")

        Returns:
            Formatted list of project versions

        Example:
            jira_get_project_versions("PROJ")
        """
        if not config.is_tool_enabled("jira_get_project_versions"):
            return "Tool is disabled by configuration"

        result = await client.get_project_versions(project_key)
        return format_versions(result)

    @mcp.tool()
    async def jira_create_version(
        project_key: str,
        name: str,
        description: str = "",
        release_date: str = "",
        start_date: str = "",
        released: bool = False,
        archived: bool = False,
    ) -> str:
        """Create a new version in a JIRA project.

        Creates a version (release) for tracking issues planned for that release.
        Versions can have start and release dates, and can be marked as released
        or archived.

        Args:
            project_key: Project key (e.g., "PROJ")
            name: Version name (e.g., "v1.0.0", "Sprint 23")
            description: Optional description of the version
            release_date: Optional release date in YYYY-MM-DD format
            start_date: Optional start date in YYYY-MM-DD format
            released: Whether the version is released (default: False)
            archived: Whether the version is archived (default: False)

        Returns:
            Created version details

        Examples:
            jira_create_version("PROJ", "v1.0.0", "First major release", "2024-12-31")
            jira_create_version("PROJ", "Sprint 23", start_date="2024-01-01", release_date="2024-01-14")
        """
        if not config.is_tool_enabled("jira_create_version"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        result = await client.create_version(
            project_key=project_key,
            name=name,
            description=description if description else None,
            release_date=release_date if release_date else None,
            start_date=start_date if start_date else None,
            released=released,
            archived=archived,
        )
        return format_version_created(result)

    @mcp.tool()
    async def jira_batch_create_versions(
        project_key: str,
        version_names: list[str],
    ) -> str:
        """Create multiple versions in a JIRA project.

        Creates multiple versions at once for a project. Useful for setting up
        a release schedule or sprint cycle.

        Args:
            project_key: Project key (e.g., "PROJ")
            version_names: List of version names to create

        Returns:
            Summary of created versions

        Example:
            jira_batch_create_versions("PROJ", ["v1.0.0", "v1.1.0", "v2.0.0"])
        """
        if not config.is_tool_enabled("jira_batch_create_versions"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        # Convert version names to version data dictionaries
        versions = [{"name": name} for name in version_names]

        result = await client.batch_create_versions(
            project_key=project_key,
            versions=versions,
        )
        return format_batch_versions(result)
