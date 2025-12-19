"""JIRA MCP Tools - All tool implementations."""

from jira_mcp.tools.issues import register_issue_tools
from jira_mcp.tools.comments import register_comment_tools
from jira_mcp.tools.transitions import register_transition_tools
from jira_mcp.tools.projects import register_project_tools
from jira_mcp.tools.boards import register_board_tools
from jira_mcp.tools.sprints import register_sprint_tools
from jira_mcp.tools.epics import register_epic_tools
from jira_mcp.tools.links import register_link_tools
from jira_mcp.tools.worklogs import register_worklog_tools
from jira_mcp.tools.versions import register_version_tools
from jira_mcp.tools.attachments import register_attachment_tools
from jira_mcp.tools.users import register_user_tools
from jira_mcp.tools.fields import register_field_tools


def register_all_tools(mcp, client, config):
    """Register all JIRA tools with the MCP server."""
    register_issue_tools(mcp, client, config)
    register_comment_tools(mcp, client, config)
    register_transition_tools(mcp, client, config)
    register_project_tools(mcp, client, config)
    register_board_tools(mcp, client, config)
    register_sprint_tools(mcp, client, config)
    register_epic_tools(mcp, client, config)
    register_link_tools(mcp, client, config)
    register_worklog_tools(mcp, client, config)
    register_version_tools(mcp, client, config)
    register_attachment_tools(mcp, client, config)
    register_user_tools(mcp, client, config)
    register_field_tools(mcp, client, config)


__all__ = ["register_all_tools"]
