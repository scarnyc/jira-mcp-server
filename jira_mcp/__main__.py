"""Entry point for running jira_mcp as a module.

Usage:
    python -m jira_mcp [OPTIONS] COMMAND [ARGS]...

Examples:
    python -m jira_mcp --version
    python -m jira_mcp serve --transport stdio
    python -m jira_mcp check
    python -m jira_mcp tools
"""

from jira_mcp.cli import main

if __name__ == "__main__":
    main()
