"""Pytest fixtures for JIRA MCP Server tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jira_mcp.config import JiraConfig


@pytest.fixture
def mock_config():
    """Create a mock JiraConfig for testing."""
    config = MagicMock(spec=JiraConfig)
    config.url = "https://test.atlassian.net"
    config.username = "test@example.com"
    config.api_token = "test-token"
    config.personal_access_token = None
    config.read_only = False
    config.enabled_tools = None
    config.enabled_tools_list = []
    config.log_level = "INFO"
    config.timeout = 30
    config.verify_ssl = True
    config.max_retries = 3
    config.is_cloud = True
    config.use_pat = False
    config.is_tool_enabled = MagicMock(return_value=True)
    return config


@pytest.fixture
def mock_config_read_only(mock_config):
    """Create a read-only mock config."""
    mock_config.read_only = True
    return mock_config


@pytest.fixture
def mock_client():
    """Create a mock JiraClient for testing."""
    client = AsyncMock()

    # Issue methods
    client.get_issue = AsyncMock(return_value={
        "key": "TEST-123",
        "fields": {
            "summary": "Test issue",
            "status": {"name": "Open"},
            "issuetype": {"name": "Bug"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Test User"},
            "reporter": {"displayName": "Reporter User"},
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-02T00:00:00.000+0000",
        }
    })

    client.create_issue = AsyncMock(return_value={
        "id": "10001",
        "key": "TEST-124",
        "self": "https://test.atlassian.net/rest/api/3/issue/10001"
    })

    client.update_issue = AsyncMock(return_value=None)
    client.delete_issue = AsyncMock(return_value=True)

    client.search_issues = AsyncMock(return_value={
        "issues": [
            {"key": "TEST-123", "fields": {"summary": "Test issue 1"}},
            {"key": "TEST-124", "fields": {"summary": "Test issue 2"}},
        ],
        "total": 2,
        "maxResults": 50,
        "startAt": 0
    })

    # Comment methods
    client.add_comment = AsyncMock(return_value={
        "id": "10001",
        "body": "Test comment",
        "author": {"displayName": "Test User"},
        "created": "2024-01-01T00:00:00.000+0000"
    })

    client.get_comments = AsyncMock(return_value={
        "comments": [
            {
                "id": "10001",
                "body": "Test comment",
                "author": {"displayName": "Test User"},
                "created": "2024-01-01T00:00:00.000+0000"
            }
        ],
        "total": 1
    })

    # Transition methods
    client.get_transitions = AsyncMock(return_value={
        "transitions": [
            {"id": "11", "name": "To Do"},
            {"id": "21", "name": "In Progress"},
            {"id": "31", "name": "Done"},
        ]
    })

    client.transition_issue = AsyncMock(return_value=None)

    # Project methods
    client.get_all_projects = AsyncMock(return_value=[
        {"key": "TEST", "name": "Test Project"},
        {"key": "PROJ", "name": "Another Project"},
    ])

    # Board methods
    client.get_agile_boards = AsyncMock(return_value={
        "values": [
            {"id": 1, "name": "Test Board", "type": "scrum"},
        ],
        "total": 1
    })

    # Sprint methods
    client.get_sprints = AsyncMock(return_value={
        "values": [
            {"id": 1, "name": "Sprint 1", "state": "active"},
        ]
    })

    # User methods
    client.get_current_user = AsyncMock(return_value={
        "displayName": "Test User",
        "emailAddress": "test@example.com",
        "accountId": "123456"
    })

    client.close = AsyncMock()

    return client


@pytest.fixture
def sample_issue():
    """Sample issue data for testing."""
    return {
        "key": "TEST-123",
        "id": "10001",
        "self": "https://test.atlassian.net/rest/api/3/issue/10001",
        "fields": {
            "summary": "Test issue summary",
            "description": "Test issue description",
            "status": {"name": "Open", "id": "1"},
            "issuetype": {"name": "Bug", "id": "1"},
            "priority": {"name": "Medium", "id": "3"},
            "project": {"key": "TEST", "name": "Test Project"},
            "assignee": {
                "displayName": "Test User",
                "emailAddress": "test@example.com",
                "accountId": "123456"
            },
            "reporter": {
                "displayName": "Reporter User",
                "emailAddress": "reporter@example.com",
                "accountId": "654321"
            },
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-02T00:00:00.000+0000",
            "labels": ["bug", "urgent"],
            "components": [{"name": "Backend"}],
        }
    }


@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "10001",
        "key": "TEST",
        "name": "Test Project",
        "projectTypeKey": "software",
        "lead": {
            "displayName": "Project Lead",
            "accountId": "lead123"
        }
    }


@pytest.fixture
def sample_sprint():
    """Sample sprint data for testing."""
    return {
        "id": 1,
        "name": "Sprint 1",
        "state": "active",
        "startDate": "2024-01-01T00:00:00.000Z",
        "endDate": "2024-01-14T00:00:00.000Z",
        "originBoardId": 1,
        "goal": "Complete feature X"
    }


@pytest.fixture
def sample_board():
    """Sample board data for testing."""
    return {
        "id": 1,
        "name": "Test Board",
        "type": "scrum",
        "location": {
            "projectKey": "TEST",
            "projectName": "Test Project"
        }
    }
