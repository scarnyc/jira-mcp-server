"""JIRA Project Tools - Project operations."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.utils.logging import get_logger


def format_projects(projects: list[dict[str, Any]]) -> str:
    """Format projects data as readable markdown.

    Args:
        projects: List of project data from JIRA API

    Returns:
        Formatted markdown string
    """
    output = f"# Projects ({len(projects)} total)\n\n"

    if not projects:
        return output + "No projects found.\n"

    for project in projects:
        key = project.get("key", "N/A")
        name = project.get("name", "N/A")
        project_type = project.get("projectTypeKey", "N/A")
        lead = project.get("lead", {}).get("displayName", "N/A")

        output += f"## {key}: {name}\n\n"
        output += f"- **Type:** {project_type}\n"
        output += f"- **Lead:** {lead}\n\n"

    return output


def register_project_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register project-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """
    logger = get_logger()

    @mcp.tool()
    async def jira_get_all_projects() -> str:
        """Get all JIRA projects.

        Retrieves a list of all projects accessible to the authenticated user.

        Returns:
            List of projects in markdown

        Example:
            jira_get_all_projects()
        """
        if not config.is_tool_enabled("jira_get_all_projects"):
            return "Tool is disabled by configuration"

        try:
            logger.info("Getting all projects")
            result = await client.get_all_projects()

            # API returns array directly
            if isinstance(result, list):
                return format_projects(result)
            else:
                return format_projects(result.get("values", []))

        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_get_project_issues(
        project_key: str,
        max_results: int = 50,
    ) -> str:
        """Get all issues for a JIRA project.

        Retrieves issues belonging to a specific project.

        Args:
            project_key: The project key (e.g., PROJ)
            max_results: Maximum number of results to return (default: 50)

        Returns:
            List of project issues in markdown

        Example:
            jira_get_project_issues("PROJ")
            jira_get_project_issues("PROJ", max_results=100)
        """
        if not config.is_tool_enabled("jira_get_project_issues"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Getting issues for project: {project_key}")
            result = await client.get_project_issues(project_key, max_results)

            issues = result.get("issues", [])
            total = result.get("total", 0)

            output = f"# Project {project_key} Issues\n\n**Total:** {total} issues (showing up to {max_results})\n\n"

            if not issues:
                return output + "No issues found.\n"

            for issue in issues:
                fields = issue.get("fields", {})
                key = issue.get("key", "N/A")
                summary = fields.get("summary", "N/A")
                status = fields.get("status", {}).get("name", "N/A")
                issue_type = fields.get("issuetype", {}).get("name", "N/A")

                output += f"- **{key}**: {summary} [{issue_type} - {status}]\n"

            return output

        except Exception as e:
            logger.error(f"Failed to get project issues: {e}")
            return f"Error: {str(e)}"
