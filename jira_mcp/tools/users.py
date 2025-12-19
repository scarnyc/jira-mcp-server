"""JIRA User Tools - Search and manage users."""

from typing import Any

from fastmcp import FastMCP

from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig


def format_user_profile(data: dict[str, Any]) -> str:
    """Format user profile into readable markdown.

    Args:
        data: User data from API

    Returns:
        Formatted markdown string
    """
    account_id = data.get("accountId", "N/A")
    display_name = data.get("displayName", "Unknown")
    email = data.get("emailAddress", "Not available")
    account_type = data.get("accountType", "Unknown")
    active = "Active" if data.get("active", False) else "Inactive"
    timezone = data.get("timeZone", "Not set")
    locale = data.get("locale", "Not set")

    # Avatar URLs
    avatar_urls = data.get("avatarUrls", {})
    avatar_48 = avatar_urls.get("48x48", "")

    return f"""# User Profile

- **Display Name:** {display_name}
- **Account ID:** {account_id}
- **Email:** {email}
- **Account Type:** {account_type}
- **Status:** {active}
- **Timezone:** {timezone}
- **Locale:** {locale}
- **Avatar:** {avatar_48}
"""


def format_user_search_results(data: dict[str, Any]) -> str:
    """Format user search results into readable markdown.

    Args:
        data: User search data from API

    Returns:
        Formatted markdown string
    """
    users = data.get("users", [])

    if not users:
        return "No users found matching the search query."

    lines = [f"# User Search Results ({len(users)} found)\n"]

    for user in users:
        display_name = user.get("displayName", "Unknown")
        account_id = user.get("accountId", "N/A")
        email = user.get("emailAddress", "Not available")
        active = "✓ Active" if user.get("active", False) else "✗ Inactive"

        lines.append(f"## {display_name}")
        lines.append(f"- **Account ID:** {account_id}")
        lines.append(f"- **Email:** {email}")
        lines.append(f"- **Status:** {active}\n")

    return "\n".join(lines)


def register_user_tools(mcp: FastMCP, client: JiraClient, config: JiraConfig) -> None:
    """Register user tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        client: JIRA API client
        config: JIRA configuration
    """

    @mcp.tool()
    async def jira_get_user_profile(account_id: str = "") -> str:
        """Get JIRA user profile information.

        Retrieves detailed profile information for a user. If no account ID is
        provided, returns the profile of the currently authenticated user.

        Args:
            account_id: Optional user account ID (empty = current user)

        Returns:
            Formatted user profile details

        Examples:
            jira_get_user_profile()  # Get current user
            jira_get_user_profile("5b10ac8d82e05b22cc7d4ef5")  # Get specific user
        """
        if not config.is_tool_enabled("jira_get_user_profile"):
            return "Tool is disabled by configuration"

        result = await client.get_user_profile(
            account_id=account_id if account_id else None
        )
        return format_user_profile(result)

    @mcp.tool()
    async def jira_search_users(
        query: str,
        max_results: int = 50,
    ) -> str:
        """Search for JIRA users by name or email.

        Searches for users matching the query string. Useful for finding account
        IDs, checking user existence, or discovering team members.

        Args:
            query: Search query (name or email)
            max_results: Maximum number of results to return (default: 50)

        Returns:
            Formatted list of matching users

        Examples:
            jira_search_users("john")
            jira_search_users("john.doe@example.com")
            jira_search_users("smith", max_results=10)
        """
        if not config.is_tool_enabled("jira_search_users"):
            return "Tool is disabled by configuration"

        result = await client.search_users(
            query=query,
            max_results=max_results,
        )
        return format_user_search_results(result)
