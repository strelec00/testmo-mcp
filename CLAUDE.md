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

## Architecture

This is a Python MCP (Model Context Protocol) server built with [FastMCP](https://github.com/jlowin/fastmcp). It exposes tools that AI assistants can call via the stdio transport.

- **`testmo-mcp.py`** — main implementation; all MCP tools are defined here using the `@mcp.tool()` decorator
- **`main.py`** — stub entry point, not used for the MCP server
- The server runs over stdio (`mcp.run(transport="stdio")`), which is how MCP clients (e.g. Claude Desktop) connect to it

### Tool pattern

Each tool is an `async` function decorated with `@mcp.tool()`. Tools call external APIs via `httpx.AsyncClient`. Return value is always a plain string that gets sent back to the caller.

### Dependencies

Managed with `uv`. Python 3.14 required (see `.python-version`). Key deps: `mcp[cli]` for the server framework, `httpx` for HTTP calls.
