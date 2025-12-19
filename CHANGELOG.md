# Changelog

## [1.0.0] - 2024-12-19

### Added
- Initial release of JIRA MCP Server
- 35 JIRA tools for complete JIRA integration
- Support for Atlassian Cloud (API Token) and Server/Data Center (PAT)
- Read-only mode for safe operations
- Tool filtering via environment variables
- Async HTTP client with retry logic
- CLI commands: serve, check, tools
- FastMCP framework integration
- Comprehensive pytest fixtures

### Tools
- **Issues**: get, create, update, delete, search, batch_create, batch_get_changelogs
- **Comments**: add, get
- **Transitions**: get, transition
- **Projects**: get_all, get_issues
- **Boards**: get_agile_boards, get_board_issues
- **Sprints**: get, get_issues, create, update
- **Epics**: link_to, get_issues
- **Links**: get_types, create, remove, create_remote
- **Worklogs**: add, get
- **Versions**: get_project, create, batch_create
- **Attachments**: download, add
- **Users**: get_profile, search
- **Fields**: search
