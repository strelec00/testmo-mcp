# testmo-mcp

MCP server for [Testmo](https://www.testmo.com) test management. Built with FastMCP.

## Installation

```bash
git clone https://github.com/your-username/testmo-mcp.git
cd testmo-mcp
uv sync
```

## Configuration

Edit `.env`:

```
TESTMO_URL=https://your-instance.testmo.net
TESTMO_API_KEY=your-api-key
```

You can find your API key in Testmo under **Settings → API Keys**.

## Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "my-mcp-testmo": {
      "command": "uv",
      "args": ["--directory", "/path/to/testmo-mcp", "run", "testmo-mcp.py"],
      "env": {
        "TESTMO_URL": "https://your-instance.testmo.net",
        "TESTMO_API_KEY": "your-api-key"
      }
    }
  }
}
```

> You can pass credentials either via `.env` file or the `env` block above — both work.

## Dev / Testing

```bash
uv run mcp dev testmo-mcp.py
```

## Tools

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

### Test Cases

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

### Test Runs

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

### Automation

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

### Issue Connections

| Tool                            | Description                            |
| ------------------------------- | -------------------------------------- |
| `testmo_list_issue_connections` | List integrations (GitHub, Jira, etc.) |
| `testmo_get_issue_connection`   | Get integration details                |

### Recursive / Composite

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
