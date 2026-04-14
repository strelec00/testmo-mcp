# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the MCP server directly
uv run testmo-mcp.py

# Run via MCP CLI (for testing tools interactively)
uv run mcp dev testmo-mcp.py
```

## Environment

Requires `TESTMO_URL` and `TESTMO_API_KEY` in `.env` (auto-loaded via python-dotenv).

## Architecture

`testmo-mcp.py` is a thin entry point that imports the `testmo/` package and runs the server. Tools are split into domain modules under `testmo/tools/`. 45 MCP tools total. Runs over stdio transport.

### Package layout

```
testmo/
  server.py        # FastMCP instance + load_dotenv
  config.py        # Constants (timeouts, limits) + FIELD_MAPPINGS
  client.py        # _request() and _upload() HTTP helpers
  tools/
    projects.py    # list_projects, get_project
    folders.py     # CRUD + find_folder_by_name; exports _get_all_folders helper
    milestones.py  # list_milestones, get_milestone
    cases.py       # CRUD + batch + search (11 tools)
    runs.py        # list_runs, get_run, list_run_results
    attachments.py # list/upload/delete case attachments (4 tools)
    automation.py  # Sources + runs + threads (9 tools)
    issues.py      # list/get issue connections
    composite.py   # Recursive folder/case ops + advanced search (3 tools)
    utility.py     # get_field_mappings, get_web_url
```

### HTTP Client

`_request()` for JSON API calls, `_upload()` for multipart uploads. Each call creates a fresh `httpx.AsyncClient` (no persistent connection).

### Tool naming

All tools are prefixed `testmo_` and use snake_case matching the Testmo API resource (e.g. `testmo_list_cases`, `testmo_batch_update_cases`).

### Pagination & rate limiting

Auto-pagination helpers (e.g. `_get_all_folders`, `testmo_get_all_cases`) loop through pages with a 0.5s delay between requests. Batch operations (create/delete) auto-chunk at 100 items per request.

### Dependencies

Managed with `uv`. Python 3.14. Key deps: `mcp[cli]`, `httpx`, `python-dotenv`.
