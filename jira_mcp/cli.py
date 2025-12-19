"""CLI interface for JIRA MCP Server."""

import asyncio
import sys
from typing import Optional

import click

from jira_mcp import __version__
from jira_mcp.utils.logging import configure_logging, get_logger


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    help="Show version and exit.",
)
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """JIRA MCP Server - A portable MCP server for JIRA integration."""
    if version:
        click.echo(f"jira-mcp-server v{__version__}")
        sys.exit(0)

    # If no subcommand, run the server
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


@main.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="MCP transport type (default: stdio)",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host for SSE transport (default: 127.0.0.1)",
)
@click.option(
    "--port",
    default=8080,
    type=int,
    help="Port for SSE transport (default: 8080)",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Override log level from config",
)
@click.option(
    "--read-only",
    is_flag=True,
    default=None,
    help="Enable read-only mode (disable write operations)",
)
def serve(
    transport: str,
    host: str,
    port: int,
    log_level: Optional[str],
    read_only: Optional[bool],
) -> None:
    """Start the JIRA MCP server."""
    from jira_mcp.config import get_config
    from jira_mcp.server import create_server

    try:
        config = get_config()
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo(
            "Ensure JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN environment variables are set.",
            err=True,
        )
        sys.exit(1)

    # Override config with CLI options
    effective_log_level = log_level or config.log_level
    configure_logging(effective_log_level)
    logger = get_logger()

    # Handle read-only override
    if read_only is not None:
        # Note: This doesn't modify the cached config, just logs the intent
        # The actual check happens at tool execution time
        if read_only:
            logger.info("Read-only mode enabled via CLI flag")

    logger.info(f"Starting JIRA MCP Server v{__version__}")
    logger.info(f"JIRA URL: {config.url}")
    logger.info(f"Transport: {transport}")
    logger.info(f"Read-only: {config.read_only or read_only}")

    # Create and run server
    mcp = create_server(config, read_only_override=read_only)

    if transport == "stdio":
        logger.info("Running with stdio transport")
        mcp.run(transport="stdio")
    else:
        logger.info(f"Running with SSE transport on {host}:{port}")
        mcp.run(transport="sse", host=host, port=port)


@main.command()
def check() -> None:
    """Check JIRA connection and configuration."""
    from jira_mcp.config import get_config
    from jira_mcp.client import JiraClient

    configure_logging("INFO")
    logger = get_logger()

    click.echo("Checking JIRA configuration...")

    try:
        config = get_config()
        click.echo(f"  JIRA URL: {config.url}")
        click.echo(f"  Username: {config.username}")
        click.echo(f"  Auth method: {'PAT' if config.use_pat else 'API Token'}")
        click.echo(f"  Cloud instance: {config.is_cloud}")
        click.echo(f"  Read-only mode: {config.read_only}")
        click.echo(f"  SSL verification: {config.verify_ssl}")
        click.echo(f"  Timeout: {config.timeout}s")
    except Exception as e:
        click.echo(f"  Configuration error: {e}", err=True)
        sys.exit(1)

    click.echo("\nTesting JIRA connection...")

    async def test_connection() -> bool:
        client = JiraClient(config)
        try:
            user = await client.get_current_user()
            click.echo(f"  Connected as: {user.get('displayName', 'Unknown')}")
            click.echo(f"  Email: {user.get('emailAddress', 'N/A')}")
            return True
        except Exception as e:
            click.echo(f"  Connection failed: {e}", err=True)
            return False
        finally:
            await client.close()

    success = asyncio.run(test_connection())

    if success:
        click.echo("\nConnection successful!")
        sys.exit(0)
    else:
        click.echo("\nConnection failed!", err=True)
        sys.exit(1)


@main.command()
def tools() -> None:
    """List available JIRA tools."""
    from jira_mcp.config import get_config

    try:
        config = get_config()
    except Exception:
        config = None

    # Tool categories and descriptions
    tool_info = {
        "Issues": [
            ("jira_get_issue", "Retrieve issue details by key"),
            ("jira_create_issue", "Create a new issue"),
            ("jira_update_issue", "Update an existing issue"),
            ("jira_delete_issue", "Delete an issue"),
            ("jira_search", "Search issues using JQL"),
            ("jira_batch_create_issues", "Create multiple issues"),
            ("jira_batch_get_changelogs", "Get issue changelogs"),
        ],
        "Comments": [
            ("jira_add_comment", "Add a comment to an issue"),
            ("jira_get_comments", "Get comments for an issue"),
        ],
        "Transitions": [
            ("jira_get_transitions", "Get available transitions"),
            ("jira_transition_issue", "Transition an issue to a new status"),
        ],
        "Projects": [
            ("jira_get_all_projects", "List all accessible projects"),
            ("jira_get_project_issues", "Get issues for a project"),
        ],
        "Boards": [
            ("jira_get_agile_boards", "List agile boards"),
            ("jira_get_board_issues", "Get issues on a board"),
        ],
        "Sprints": [
            ("jira_get_sprints_from_board", "Get sprints for a board"),
            ("jira_get_sprint_issues", "Get issues in a sprint"),
            ("jira_create_sprint", "Create a new sprint"),
            ("jira_update_sprint", "Update a sprint"),
        ],
        "Epics": [
            ("jira_link_to_epic", "Link an issue to an epic"),
            ("jira_get_epic_issues", "Get issues in an epic"),
        ],
        "Links": [
            ("jira_get_link_types", "Get available link types"),
            ("jira_create_issue_link", "Create a link between issues"),
            ("jira_remove_issue_link", "Remove a link between issues"),
            ("jira_create_remote_issue_link", "Create an external link"),
        ],
        "Worklogs": [
            ("jira_add_worklog", "Log time on an issue"),
            ("jira_get_worklog", "Get worklogs for an issue"),
        ],
        "Versions": [
            ("jira_get_project_versions", "Get versions for a project"),
            ("jira_create_version", "Create a new version"),
            ("jira_batch_create_versions", "Create multiple versions"),
        ],
        "Attachments": [
            ("jira_download_attachments", "Download attachments"),
            ("jira_add_attachment", "Add an attachment to an issue"),
        ],
        "Users": [
            ("jira_get_user_profile", "Get user profile"),
            ("jira_search_users", "Search for users"),
        ],
        "Fields": [
            ("jira_search_fields", "Search for field definitions"),
        ],
    }

    click.echo("Available JIRA MCP Tools:\n")

    enabled_tools = config.enabled_tools_list if config else []
    read_only = config.read_only if config else False

    write_tools = {
        "jira_create_issue",
        "jira_update_issue",
        "jira_delete_issue",
        "jira_batch_create_issues",
        "jira_add_comment",
        "jira_transition_issue",
        "jira_create_sprint",
        "jira_update_sprint",
        "jira_link_to_epic",
        "jira_create_issue_link",
        "jira_remove_issue_link",
        "jira_create_remote_issue_link",
        "jira_add_worklog",
        "jira_create_version",
        "jira_batch_create_versions",
        "jira_add_attachment",
    }

    total_tools = 0
    for category, tools_list in tool_info.items():
        click.echo(f"  {category}:")
        for tool_name, description in tools_list:
            total_tools += 1
            status = ""

            # Check if tool is disabled
            if enabled_tools and tool_name not in enabled_tools:
                status = " [DISABLED]"
            elif read_only and tool_name in write_tools:
                status = " [READ-ONLY]"

            click.echo(f"    - {tool_name}: {description}{status}")
        click.echo()

    click.echo(f"Total: {total_tools} tools")

    if read_only:
        click.echo("\nNote: Write operations are disabled (read-only mode)")


if __name__ == "__main__":
    main()
