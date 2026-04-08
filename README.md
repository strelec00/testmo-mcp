# Testmo MCP Server

> **A Python [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for [Testmo](https://www.testmo.com) — bring AI-assisted test management to Claude Desktop, Cursor, and any MCP-compatible client.**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![FastMCP](https://img.shields.io/badge/built%20with-FastMCP-purple)](https://github.com/jlowin/fastmcp)
[![MCP](https://img.shields.io/badge/MCP-compatible-green)](https://modelcontextprotocol.io)

**Testmo MCP** is an open-source MCP server that connects AI assistants like **Claude Desktop**, **Claude Code**, and **Cursor** directly to your **Testmo test management** instance. Manage test cases, folders, milestones, runs, attachments, and CI/CD automation sources — all through natural language, without leaving your AI client.

Built for QA engineers, SDETs, and developers who use Testmo and want to stop clicking through the UI for repetitive work. Powered by [FastMCP](https://github.com/jlowin/fastmcp) and the Testmo REST API.

---

## ✨ Features

- 🧪 **Full test case management** — create, read, update, delete, search, and bulk-operate on Testmo cases
- 📁 **Folder operations** — create, rename, move, delete, and traverse folder trees recursively
- 🚀 **Bulk & batch operations** — create or update up to 100 cases per call, or unlimited with auto-batching
- 🏃 **Test runs & results** — list runs, fetch run details, and filter run results
- 🎯 **Milestones** — list and inspect milestones across projects
- 📎 **Attachments** — upload, list, and delete file attachments on test cases
- 🤖 **CI/CD automation sources** — manage automation runs, parallel threads, and result submission
- 🔗 **Issue integrations** — list GitHub, Jira, and other issue connections
- 🌳 **Recursive helpers** — fetch entire folder subtrees of cases in one call
- 🛠️ **Field mapping utilities** — resolve priority, type, and state IDs without guessing
- 🤝 **Works with any MCP client** — Claude Desktop, Claude Code, Cursor, Cline, and more

---

## 🚀 Quick start

### Prerequisites

- Python 3.11 or newer
- [`uv`](https://github.com/astral-sh/uv) package manager
- A Testmo instance and API key (**Settings → API Keys** in Testmo)
- An MCP-compatible client (Claude Desktop, Cursor, etc.)

### Installation

```bash
git clone https://github.com/strelec00/testmo-mcp.git
cd testmo-mcp
uv sync
```

### Configuration

Create a `.env` file in the project root:

```bash
TESTMO_URL=https://your-instance.testmo.net
TESTMO_API_KEY=your-api-key
```

### Connect to Claude Desktop

Add this to your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "testmo": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/testmo-mcp",
        "run",
        "testmo-mcp.py"
      ],
      "env": {
        "TESTMO_URL": "https://your-instance.testmo.net",
        "TESTMO_API_KEY": "your-api-key"
      }
    }
  }
}
```

Restart Claude Desktop. The Testmo tools will appear in the MCP tools list.

> 💡 You can pass credentials via either `.env` or the `env` block above — both work.

### Connect to Cursor

Open **Cursor Settings → MCP** (or edit `~/.cursor/mcp.json`) and use the same JSON snippet.

### Dev / testing mode

```bash
uv run mcp dev testmo-mcp.py
```

---

## 💬 Example prompts

Once connected, try asking your AI assistant:

- _"List all projects in Testmo and show me the one called Certilligent."_
- _"Create 20 login test cases covering valid credentials, wrong password, locked account, expired session, and 2FA flows."_
- _"Find the 'Smoke Tests' folder and list every high-priority case inside it recursively."_
- _"Bulk update all draft cases in folder 42 to set their priority to high."_
- _"Show me the latest automation run for the Playwright source and append a new thread of results."_
- _"Upload this screenshot as an attachment to test case 1234."_

---

## 🧠 Why use Testmo with MCP?

Traditional Testmo workflows require navigating the UI for every test case, every folder, every bulk update. With **Testmo MCP**, your AI assistant becomes a QA co-pilot:

- Spin up entire test suites from a feature spec or PRD in seconds
- Refactor folder structures conversationally instead of click-by-click
- Keep Testmo in sync with your codebase without context-switching
- Pair with **Claude Code** for end-to-end QA automation: generate Playwright tests _and_ register them in Testmo
- Wire CI/CD automation runs straight from your terminal session

---

## 🔧 Available tools

### Projects

| Tool                   | Description         |
| ---------------------- | ------------------- |
| `testmo_list_projects` | List all projects   |
| `testmo_get_project`   | Get project details |

### Folders

| Tool                         | Description                  |
| ---------------------------- | ---------------------------- |
| `testmo_list_folders`        | List folders with full paths |
| `testmo_get_folder`          | Get folder details           |
| `testmo_create_folder`       | Create folder                |
| `testmo_update_folder`       | Update folder name/parent    |
| `testmo_delete_folder`       | Delete folder and its cases  |
| `testmo_find_folder_by_name` | Find folder by name          |

### Test cases

| Tool                        | Description                           |
| --------------------------- | ------------------------------------- |
| `testmo_list_cases`         | List cases (paginated)                |
| `testmo_get_all_cases`      | Get all cases (auto-pagination)       |
| `testmo_get_case`           | Get single case details               |
| `testmo_create_case`        | Create one case                       |
| `testmo_create_cases`       | Create up to 100 cases                |
| `testmo_batch_create_cases` | Create unlimited cases (auto-batched) |
| `testmo_update_case`        | Update one case                       |
| `testmo_batch_update_cases` | Bulk update up to 100 cases           |
| `testmo_delete_case`        | Delete one case                       |
| `testmo_batch_delete_cases` | Delete multiple cases (auto-batched)  |
| `testmo_search_cases`       | Search cases with filters             |

### Milestones

| Tool                     | Description           |
| ------------------------ | --------------------- |
| `testmo_list_milestones` | List milestones       |
| `testmo_get_milestone`   | Get milestone details |

### Test runs

| Tool                      | Description                   |
| ------------------------- | ----------------------------- |
| `testmo_list_runs`        | List test runs                |
| `testmo_get_run`          | Get run details               |
| `testmo_list_run_results` | List run results with filters |

### Attachments

| Tool                             | Description           |
| -------------------------------- | --------------------- |
| `testmo_list_case_attachments`   | List case attachments |
| `testmo_upload_case_attachment`  | Upload file (base64)  |
| `testmo_delete_case_attachments` | Delete attachments    |

### Automation (CI/CD)

| Tool                                    | Description                   |
| --------------------------------------- | ----------------------------- |
| `testmo_list_automation_sources`        | List CI/CD sources            |
| `testmo_get_automation_source`          | Get source details            |
| `testmo_list_automation_runs`           | List automation runs          |
| `testmo_get_automation_run`             | Get automation run details    |
| `testmo_create_automation_run`          | Create automation run         |
| `testmo_append_automation_run`          | Append artifacts/fields/links |
| `testmo_complete_automation_run`        | Complete automation run       |
| `testmo_create_automation_run_thread`   | Create parallel thread        |
| `testmo_append_automation_run_thread`   | Submit test results to thread |
| `testmo_complete_automation_run_thread` | Complete thread               |

### Issue connections

| Tool                            | Description                            |
| ------------------------------- | -------------------------------------- |
| `testmo_list_issue_connections` | List integrations (GitHub, Jira, etc.) |
| `testmo_get_issue_connection`   | Get integration details                |

### Recursive / composite

| Tool                            | Description                    |
| ------------------------------- | ------------------------------ |
| `testmo_get_folders_recursive`  | Get folder tree                |
| `testmo_get_cases_recursive`    | Get all cases from folder tree |
| `testmo_search_cases_recursive` | Search within folder subtree   |

### Utility

| Tool                        | Description                                     |
| --------------------------- | ----------------------------------------------- |
| `testmo_get_field_mappings` | Get field value IDs (priorities, types, states) |
| `testmo_get_web_url`        | Generate Testmo web URL                         |

---

## 🛠️ Troubleshooting

**"Tool not found" in Claude Desktop**
Use an absolute path in `args` and fully restart Claude Desktop after editing the config.

**`401 Unauthorized`**
Double-check `TESTMO_API_KEY` and that the key has API access enabled in Testmo under **Settings → API Keys**.

**`uv: command not found`**
Install [uv](https://github.com/astral-sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## 🤝 Contributing

PRs welcome. Open an issue first for larger changes.

---

## 📄 License

MIT

---

## 🔗 Related projects

- [Testmo](https://www.testmo.com) — unified test management for software teams
- [Model Context Protocol](https://modelcontextprotocol.io) — open standard for AI tool integrations
- [FastMCP](https://github.com/jlowin/fastmcp) — Pythonic framework for building MCP servers
- [Claude Desktop](https://claude.ai/download) — Anthropic's desktop client with MCP support

---

**Keywords:** testmo mcp, testmo claude, testmo ai integration, mcp server testmo, model context protocol testmo, testmo python, testmo api client, fastmcp testmo, ai test management, qa automation claude, testmo cursor, testmo automation api, testmo bulk create cases, anthropic mcp servers
