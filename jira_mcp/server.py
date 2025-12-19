"""FastMCP server setup for JIRA MCP Server."""

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastmcp import FastMCP

from jira_mcp import __version__
from jira_mcp.client import JiraClient
from jira_mcp.config import JiraConfig
from jira_mcp.tools import register_all_tools
from jira_mcp.utils.logging import get_logger


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[dict]:
    """Manage server lifecycle - initialize and cleanup JIRA client.

    Args:
        mcp: FastMCP server instance

    Yields:
        Context dictionary with JIRA client
    """
    logger = get_logger()
    logger.info("Initializing JIRA MCP Server...")

    # Get config from server context
    config: JiraConfig = mcp.context.get("config")
    read_only_override: Optional[bool] = mcp.context.get("read_only_override")

    # Create JIRA client
    client = JiraClient(config)

    # Store in context for tools to access
    context = {
        "client": client,
        "config": config,
        "read_only": read_only_override if read_only_override is not None else config.read_only,
    }

    logger.info(f"Connected to JIRA: {config.url}")
    logger.info(f"Read-only mode: {context['read_only']}")

    try:
        yield context
    finally:
        logger.info("Shutting down JIRA MCP Server...")
        await client.close()
        logger.info("JIRA client closed")


def create_server(
    config: JiraConfig,
    read_only_override: Optional[bool] = None,
) -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        config: JIRA configuration
        read_only_override: Override read-only setting from config

    Returns:
        Configured FastMCP server instance
    """
    logger = get_logger()

    # Create FastMCP server
    mcp = FastMCP(
        name="jira-mcp-server",
        version=__version__,
        description="A portable MCP server for JIRA integration with Claude Code",
        lifespan=lifespan,
    )

    # Store config in server context for lifespan to access
    mcp.context = {
        "config": config,
        "read_only_override": read_only_override,
    }

    # Determine effective read-only setting
    effective_read_only = (
        read_only_override if read_only_override is not None else config.read_only
    )

    # Create a temporary client for tool registration (will be replaced in lifespan)
    # This is needed because tools are registered before the server starts
    temp_client = JiraClient(config)

    # Register all tools
    logger.info("Registering JIRA tools...")
    register_all_tools(mcp, temp_client, config)
    logger.info("All JIRA tools registered")

    return mcp
