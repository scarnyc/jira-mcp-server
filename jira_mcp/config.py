"""Configuration management for JIRA MCP Server using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class JiraConfig(BaseSettings):
    """JIRA MCP Server configuration.

    All settings can be configured via environment variables with the JIRA_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="JIRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required settings
    url: str = Field(
        ...,
        description="JIRA instance URL (e.g., https://your-domain.atlassian.net)",
    )
    username: str = Field(
        ...,
        description="JIRA username (email for Atlassian Cloud)",
    )
    api_token: str = Field(
        ...,
        description="JIRA API token or Personal Access Token (PAT)",
    )

    # Optional settings
    read_only: bool = Field(
        default=False,
        description="When true, disable all write operations",
    )
    enabled_tools: Optional[str] = Field(
        default=None,
        description="Comma-separated list of enabled tools (empty = all tools)",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=5,
        le=300,
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed requests",
        ge=0,
        le=10,
    )
    personal_access_token: Optional[str] = Field(
        default=None,
        description="Personal Access Token (alternative to username/api_token)",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is properly formatted."""
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @property
    def enabled_tools_list(self) -> list[str]:
        """Get list of enabled tools."""
        if not self.enabled_tools:
            return []
        return [t.strip() for t in self.enabled_tools.split(",") if t.strip()]

    @property
    def is_cloud(self) -> bool:
        """Check if this is an Atlassian Cloud instance."""
        return "atlassian.net" in self.url

    @property
    def use_pat(self) -> bool:
        """Check if Personal Access Token should be used."""
        return self.personal_access_token is not None

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled."""
        enabled = self.enabled_tools_list
        if not enabled:
            return True  # All tools enabled by default
        return tool_name in enabled


@lru_cache
def get_config() -> JiraConfig:
    """Get cached configuration singleton."""
    return JiraConfig()
