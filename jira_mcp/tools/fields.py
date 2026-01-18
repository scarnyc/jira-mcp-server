"""JIRA Field Tools - Field metadata operations."""

from typing import Any, Optional

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.utils.logging import get_logger


def format_fields(fields: list[dict[str, Any]]) -> str:
    """Format fields data as readable markdown.

    Args:
        fields: List of field data from JIRA API

    Returns:
        Formatted markdown string
    """
    output = f"# JIRA Fields ({len(fields)} total)\n\n"

    if not fields:
        return output + "No fields found.\n"

    for field in fields:
        field_id = field.get("id", "N/A")
        name = field.get("name", "N/A")
        field_type = field.get("schema", {}).get("type", "N/A")
        custom = field.get("custom", False)
        field_type_label = "Custom" if custom else "System"

        output += f"## {name}\n\n"
        output += f"- **ID:** `{field_id}`\n"
        output += f"- **Type:** {field_type}\n"
        output += f"- **Category:** {field_type_label}\n\n"

    return output


def register_field_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register field-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """
    logger = get_logger()

    @mcp.tool()
    async def jira_search_fields(query: Optional[str] = None) -> str:
        """Search JIRA field definitions.

        Retrieves metadata about JIRA fields including custom fields, system fields,
        and their schemas. Useful for understanding available fields when creating
        or updating issues.

        Args:
            query: Optional search query to filter fields by name (default: None, returns all)

        Returns:
            Field definitions in markdown

        Example:
            jira_search_fields()
            jira_search_fields("assignee")
            jira_search_fields("custom")
        """
        if not config.is_tool_enabled("jira_search_fields"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Searching fields{f' with query: {query}' if query else ''}")
            result = await client.get_fields()

            # API returns array directly
            if isinstance(result, list):
                fields = result
            else:
                fields = result.get("values", [])

            # Filter by query if provided (client-side filtering as backup)
            if query:
                query_lower = query.lower()
                fields = [
                    f for f in fields
                    if query_lower in f.get("name", "").lower()
                    or query_lower in f.get("id", "").lower()
                ]

            return format_fields(fields)

        except Exception as e:
            logger.error(f"Failed to search fields: {e}")
            return f"Error: {str(e)}"
