"""JIRA Attachment Tools - Manage issue attachments."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_attachments(data: dict[str, Any]) -> str:
    """Format attachments list into readable markdown.

    Args:
        data: Attachments data from API

    Returns:
        Formatted markdown string
    """
    attachments = data.get("attachments", [])

    if not attachments:
        return "No attachments found for this issue."

    lines = ["# Attachments\n"]
    total_size = 0

    for attachment in attachments:
        filename = attachment.get("filename", "Unknown")
        size = attachment.get("size", 0)
        author = attachment.get("author", {}).get("displayName", "Unknown")
        created = attachment.get("created", "N/A")
        mime_type = attachment.get("mimeType", "unknown")
        content_url = attachment.get("content", "")

        # Convert size to human-readable format
        size_kb = size / 1024
        size_str = f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"

        total_size += size

        lines.append(f"## {filename}")
        lines.append(f"- **Size:** {size_str}")
        lines.append(f"- **Type:** {mime_type}")
        lines.append(f"- **Author:** {author}")
        lines.append(f"- **Created:** {created}")
        lines.append(f"- **URL:** {content_url}\n")

    # Total size
    total_kb = total_size / 1024
    total_str = f"{total_kb:.2f} KB" if total_kb < 1024 else f"{total_kb / 1024:.2f} MB"
    lines.insert(1, f"**Total Size:** {total_str}\n")
    lines.insert(1, f"**Total Attachments:** {len(attachments)}")

    return "\n".join(lines)


def format_attachment_uploaded(data: dict[str, Any]) -> str:
    """Format uploaded attachment into readable markdown.

    Args:
        data: Attachment data from API

    Returns:
        Formatted markdown string
    """
    attachments = data.get("attachments", [])

    if not attachments:
        return "Attachment uploaded successfully."

    lines = ["# Attachment Uploaded\n"]

    for attachment in attachments:
        filename = attachment.get("filename", "Unknown")
        size = attachment.get("size", 0)
        attachment_id = attachment.get("id", "N/A")

        # Convert size to human-readable format
        size_kb = size / 1024
        size_str = f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"

        lines.append(f"- **File:** {filename}")
        lines.append(f"- **ID:** {attachment_id}")
        lines.append(f"- **Size:** {size_str}")

    return "\n".join(lines)


def register_attachment_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register attachment tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_download_attachments(issue_key: str) -> str:
        """Get attachment metadata for a JIRA issue.

        Returns information about all attachments on an issue, including download
        URLs, file sizes, and metadata. Note: This returns metadata only; actual
        file downloads would need to be performed separately using the content URL.

        Args:
            issue_key: Issue key to get attachments for

        Returns:
            Formatted list of attachment metadata with download URLs

        Example:
            jira_download_attachments("PROJ-123")
        """
        if not config.is_tool_enabled("jira_download_attachments"):
            return "Tool is disabled by configuration"

        issue = await client.get_issue(issue_key, fields=["attachment"])
        attachments = issue.get("fields", {}).get("attachment", [])
        result = {"attachments": attachments}
        return format_attachments(result)

    @mcp.tool()
    async def jira_add_attachment(
        issue_key: str,
        file_path: str,
        filename: str = "",
    ) -> str:
        """Upload an attachment to a JIRA issue.

        Adds a file attachment to an issue. The file must be accessible on the
        local filesystem.

        Args:
            issue_key: Issue key to attach file to
            file_path: Path to the file to upload (must exist)
            filename: Optional custom filename (defaults to file's basename)

        Returns:
            Success message with attachment details

        Examples:
            jira_add_attachment("PROJ-123", "/path/to/screenshot.png")
            jira_add_attachment("PROJ-456", "/path/to/doc.pdf", "requirements.pdf")
        """
        if not config.is_tool_enabled("jira_add_attachment"):
            return "Tool is disabled by configuration"

        if config.read_only:
            return "Operation not allowed: Server is in read-only mode"

        result = await client.add_attachment(
            key=issue_key,
            file_path=file_path,
            filename=filename if filename else None,
        )
        return format_attachment_uploaded(result)
