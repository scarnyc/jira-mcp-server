"""JIRA Transition Tools - Workflow transition operations."""

from typing import Any, Optional

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.utils.logging import get_logger


def format_transitions(transitions_data: dict[str, Any]) -> str:
    """Format transitions data as readable markdown.

    Args:
        transitions_data: Transitions data from JIRA API

    Returns:
        Formatted markdown string
    """
    transitions = transitions_data.get("transitions", [])

    output = "# Available Transitions\n\n"

    if not transitions:
        return output + "No transitions available for this issue.\n"

    for transition in transitions:
        trans_id = transition.get("id", "N/A")
        name = transition.get("name", "N/A")
        to_status = transition.get("to", {}).get("name", "N/A")

        output += f"- **{name}** (ID: {trans_id}) → {to_status}\n"

    return output


def register_transition_tools(
    mcp: FastMCP, client: JiraClient, config: JiraConfig
) -> None:
    """Register transition-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """
    logger = get_logger()

    @mcp.tool()
    async def jira_get_transitions(issue_key: str) -> str:
        """Get available workflow transitions for a JIRA issue.

        Retrieves all transitions that can be performed on the issue based on
        its current status and the workflow configuration.

        Args:
            issue_key: The issue key (e.g., PROJ-123)

        Returns:
            List of available transitions in markdown

        Example:
            jira_get_transitions("PROJ-123")
        """
        if not config.is_tool_enabled("jira_get_transitions"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Getting transitions for issue: {issue_key}")
            result = await client.get_transitions(issue_key)
            return format_transitions(result)
        except Exception as e:
            logger.error(f"Failed to get transitions for {issue_key}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_transition_issue(
        issue_key: str,
        transition_name: str,
        resolution: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        """Transition a JIRA issue to a new status.

        Moves an issue through the workflow by applying a transition. This changes
        the issue's status (e.g., from "To Do" to "In Progress").

        Args:
            issue_key: The issue key (e.g., PROJ-123)
            transition_name: Name of the transition (e.g., "Start Progress", "Done")
            resolution: Resolution name if transitioning to a closed status (optional)
            comment: Comment to add when transitioning (optional)

        Returns:
            Confirmation message

        Example:
            jira_transition_issue("PROJ-123", "Start Progress")
            jira_transition_issue("PROJ-123", "Done", resolution="Fixed", comment="Bug fixed")
        """
        if not config.is_tool_enabled("jira_transition_issue"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot transition issue - server is in read-only mode"

        try:
            logger.info(f"Transitioning issue {issue_key} to: {transition_name}")

            # First, get available transitions to find the ID
            transitions_data = await client.get_transitions(issue_key)
            transitions = transitions_data.get("transitions", [])

            # Find the transition ID by name
            transition_id = None
            for transition in transitions:
                if transition.get("name", "").lower() == transition_name.lower():
                    transition_id = transition.get("id")
                    break

            if not transition_id:
                available = [t.get("name", "N/A") for t in transitions]
                return f"Error: Transition '{transition_name}' not found. Available transitions: {', '.join(available)}"

            # Build fields for transition
            fields = {}
            if resolution:
                fields["resolution"] = {"name": resolution}

            # Execute transition
            await client.transition_issue(issue_key, transition_id, fields if fields else None)

            # Add comment if provided
            comment_msg = ""
            if comment:
                adf_body = {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}],
                        }
                    ],
                }
                await client.add_comment(issue_key, adf_body)
                comment_msg = "\n✅ Comment added"

            # Get updated issue to show new status
            updated_issue = await client.get_issue(issue_key)
            new_status = updated_issue.get("fields", {}).get("status", {}).get("name", "N/A")

            return f"""✅ Issue transitioned successfully!

**Issue:** {issue_key}
**Transition:** {transition_name}
**New Status:** {new_status}{comment_msg}
"""
        except Exception as e:
            logger.error(f"Failed to transition issue {issue_key}: {e}")
            return f"Error: {str(e)}"
