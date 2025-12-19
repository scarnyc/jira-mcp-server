"""Authentication utilities for JIRA API."""

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jira_mcp.config import JiraConfig


def get_auth_headers(config: "JiraConfig") -> dict[str, str]:
    """Generate authentication headers for JIRA API requests.

    Args:
        config: JIRA configuration object

    Returns:
        Dictionary of authentication headers
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if config.use_pat:
        # Personal Access Token authentication (JIRA Server/Data Center)
        headers["Authorization"] = f"Bearer {config.personal_access_token}"
    else:
        # Basic authentication with API token (Atlassian Cloud)
        credentials = f"{config.username}:{config.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"

    return headers
