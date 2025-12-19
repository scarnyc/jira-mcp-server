"""JIRA MCP Server - A portable MCP server for JIRA integration."""

__version__ = "1.0.0"
__author__ = "scarnyc"

from jira_mcp.server import create_server

__all__ = ["create_server", "__version__"]
