# JIRA MCP Server

A portable MCP (Model Context Protocol) server for JIRA integration with Claude Code and other MCP-compatible clients.

## Features

- **35 JIRA Tools** - Complete coverage of JIRA operations
- **Portable** - Install via pip from GitHub, use in any project
- **Multiple Auth Methods** - API Token (Cloud) and PAT (Server/Data Center)
- **Read-Only Mode** - Safely disable write operations
- **Tool Filtering** - Enable/disable specific tools
- **Async** - Built on httpx for efficient async operations

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/scarnyc/jira-mcp-server

# Or clone and install locally
git clone https://github.com/scarnyc/jira-mcp-server
cd jira-mcp-server
pip install -e .
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your-api-token

# Optional
JIRA_READ_ONLY=false          # Disable write operations
JIRA_ENABLED_TOOLS=           # Comma-separated tool names (empty = all)
JIRA_LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR
JIRA_TIMEOUT=30               # Request timeout in seconds
JIRA_VERIFY_SSL=true          # SSL certificate verification
```

### Getting API Token

1. Go to [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Copy the token and set as `JIRA_API_TOKEN`

### Claude Code Integration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "jira-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "JIRA_URL": "${JIRA_URL}",
        "JIRA_USERNAME": "${JIRA_USERNAME}",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    }
  }
}
```

Then restart Claude Code and verify with `/mcp`.

## Usage

### CLI Commands

```bash
# Start the MCP server (stdio transport)
jira-mcp serve

# Start with SSE transport
jira-mcp serve --transport sse --port 8080

# Check connection
jira-mcp check

# List available tools
jira-mcp tools

# Show version
jira-mcp --version
```

### With Claude Code

Once configured, you can use natural language to interact with JIRA:

```
> What's the status of PROJ-123?

> Create a bug: Login fails on slow connections

> Move PROJ-123 to In Progress

> Show me all unresolved bugs in the PROJ project

> Add comment to PROJ-123: Started implementation

> What's in the current sprint?
```

## Available Tools

### Issues (7 tools)
| Tool | Description |
|------|-------------|
| `jira_get_issue` | Get issue details by key |
| `jira_create_issue` | Create a new issue |
| `jira_update_issue` | Update an existing issue |
| `jira_delete_issue` | Delete an issue |
| `jira_search` | Search issues using JQL |
| `jira_batch_create_issues` | Create multiple issues |
| `jira_batch_get_changelogs` | Get issue change history |

### Comments (2 tools)
| Tool | Description |
|------|-------------|
| `jira_add_comment` | Add a comment to an issue |
| `jira_get_comments` | Get comments for an issue |

### Transitions (2 tools)
| Tool | Description |
|------|-------------|
| `jira_get_transitions` | Get available workflow transitions |
| `jira_transition_issue` | Move issue to a new status |

### Projects (2 tools)
| Tool | Description |
|------|-------------|
| `jira_get_all_projects` | List all accessible projects |
| `jira_get_project_issues` | Get issues for a project |

### Boards (2 tools)
| Tool | Description |
|------|-------------|
| `jira_get_agile_boards` | List agile boards |
| `jira_get_board_issues` | Get issues on a board |

### Sprints (4 tools)
| Tool | Description |
|------|-------------|
| `jira_get_sprints_from_board` | Get sprints for a board |
| `jira_get_sprint_issues` | Get issues in a sprint |
| `jira_create_sprint` | Create a new sprint |
| `jira_update_sprint` | Update a sprint |

### Epics (2 tools)
| Tool | Description |
|------|-------------|
| `jira_link_to_epic` | Link an issue to an epic |
| `jira_get_epic_issues` | Get issues in an epic |

### Links (4 tools)
| Tool | Description |
|------|-------------|
| `jira_get_link_types` | Get available link types |
| `jira_create_issue_link` | Create a link between issues |
| `jira_remove_issue_link` | Remove a link |
| `jira_create_remote_issue_link` | Create an external link |

### Worklogs (2 tools)
| Tool | Description |
|------|-------------|
| `jira_add_worklog` | Log time on an issue |
| `jira_get_worklog` | Get worklogs for an issue |

### Versions (3 tools)
| Tool | Description |
|------|-------------|
| `jira_get_project_versions` | Get versions for a project |
| `jira_create_version` | Create a new version |
| `jira_batch_create_versions` | Create multiple versions |

### Attachments (2 tools)
| Tool | Description |
|------|-------------|
| `jira_download_attachments` | Download attachments |
| `jira_add_attachment` | Add an attachment |

### Users (2 tools)
| Tool | Description |
|------|-------------|
| `jira_get_user_profile` | Get user profile |
| `jira_search_users` | Search for users |

### Fields (1 tool)
| Tool | Description |
|------|-------------|
| `jira_search_fields` | Get field definitions |

## Read-Only Mode

To prevent accidental modifications, enable read-only mode:

```bash
JIRA_READ_ONLY=true
```

Or via CLI:

```bash
jira-mcp serve --read-only
```

Write operations will return an error message when read-only mode is enabled.

## Tool Filtering

Enable only specific tools:

```bash
JIRA_ENABLED_TOOLS=jira_get_issue,jira_search,jira_get_transitions
```

Disabled tools will return an error message when invoked.

## Development

```bash
# Clone the repository
git clone https://github.com/scarnyc/jira-mcp-server
cd jira-mcp-server

# Install with Poetry
poetry install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=jira_mcp --cov-report=html

# Lint and format
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy jira_mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.
