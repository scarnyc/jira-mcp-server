"""JIRA Comment Tools - Comment operations."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.utils.logging import get_logger


def format_comments(comments_data: dict[str, Any]) -> str:
    """Format comments data as readable markdown.

    Args:
        comments_data: Comments data from JIRA API

    Returns:
        Formatted markdown string
    """
    comments = comments_data.get("comments", [])
    total = comments_data.get("total", 0)

    output = f"# Comments ({total} total)\n\n"

    if not comments:
        return output + "No comments found.\n"

    for comment in comments:
        author = comment.get("author", {}).get("displayName", "Unknown")
        created = comment.get("created", "N/A")
        body = comment.get("body", "")

        # Handle Atlassian Document Format (ADF)
        if isinstance(body, dict):
            body = _extract_text_from_adf(body)

        output += f"## {author} - {created}\n\n{body}\n\n---\n\n"

    return output


def _extract_text_from_adf(adf: dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format.

    Args:
        adf: ADF document structure

    Returns:
        Extracted text
    """
    if not isinstance(adf, dict):
        return str(adf)

    text_parts = []
    content = adf.get("content", [])

    for node in content:
        if node.get("type") == "paragraph":
            para_content = node.get("content", [])
            para_text = []
            for text_node in para_content:
                if text_node.get("type") == "text":
                    para_text.append(text_node.get("text", ""))
            text_parts.append("".join(para_text))

    return "\n\n".join(text_parts) if text_parts else ""


def register_comment_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register comment-related tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """
    logger = get_logger()

    @mcp.tool()
    async def jira_add_comment(issue_key: str, comment: str) -> str:
        """Add a comment to a JIRA issue.

        Posts a new comment on the specified issue.

        Args:
            issue_key: The issue key (e.g., PROJ-123)
            comment: The comment text to add

        Returns:
            Confirmation message with comment details

        Example:
            jira_add_comment("PROJ-123", "This has been fixed in the latest release")
        """
        if not config.is_tool_enabled("jira_add_comment"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Error: Cannot add comment - server is in read-only mode"

        try:
            logger.info(f"Adding comment to issue: {issue_key}")

            # Convert plain text to ADF format
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

            result = await client.add_comment(issue_key, adf_body)

            author = result.get("author", {}).get("displayName", "Unknown")
            created = result.get("created", "N/A")
            comment_id = result.get("id", "N/A")

            return f"""✅ Comment added successfully!

**Comment ID:** {comment_id}
**Author:** {author}
**Created:** {created}

**Comment:**
{comment}
"""
        except Exception as e:
            logger.error(f"Failed to add comment to {issue_key}: {e}")
            return f"Error: {str(e)}"

    @mcp.tool()
    async def jira_get_comments(issue_key: str) -> str:
        """Get all comments for a JIRA issue.

        Retrieves all comments posted on the specified issue.

        Args:
            issue_key: The issue key (e.g., PROJ-123)

        Returns:
            All comments in markdown format

        Example:
            jira_get_comments("PROJ-123")
        """
        if not config.is_tool_enabled("jira_get_comments"):
            return "Tool is disabled by configuration"

        try:
            logger.info(f"Getting comments for issue: {issue_key}")
            result = await client.get_comments(issue_key)
            return format_comments(result)
        except Exception as e:
            logger.error(f"Failed to get comments for {issue_key}: {e}")
            return f"Error: {str(e)}"
