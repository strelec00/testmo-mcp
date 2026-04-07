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

Single-file FastMCP server (`testmo-mcp.py`) that wraps the Testmo REST API into 44 MCP tools. Runs over stdio transport.

### Sections in testmo-mcp.py

1. **Config** — `FIELD_MAPPINGS` dict with all Testmo field value IDs (priorities, types, states, etc.)
2. **HTTP Client** — `_request()` for JSON API calls, `_upload_file()` for multipart uploads. Each call creates a fresh `httpx.AsyncClient` (no persistent connection).
3. **Tools by domain** — Projects, Folders, Milestones, Cases (CRUD + search + batch), Runs, Run Results, Attachments, Automation Sources, Automation Runs (full lifecycle with threads), Issue Connections, Composite (recursive folder/case operations), Utility.

### Tool naming

All tools are prefixed `testmo_` and use snake_case matching the Testmo API resource (e.g. `testmo_list_cases`, `testmo_batch_update_cases`).

### Pagination & rate limiting

Auto-pagination helpers (e.g. `_get_all_folders`, `testmo_get_all_cases`) loop through pages with a 0.5s delay between requests. Batch operations (create/delete) auto-chunk at 100 items per request.

### Dependencies

Managed with `uv`. Python 3.14. Key deps: `mcp[cli]`, `httpx`, `python-dotenv`.
