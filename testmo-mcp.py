"""
Testmo MCP Server — FastMCP implementation.

Provides tools for AI assistants to manage test cases, folders, projects,
runs, automation runs, attachments, and more via the Testmo REST API.
"""

import asyncio
import io
import json
import mimetypes
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("testmo-mcp")

# =============================================================================
# Configuration
# =============================================================================

TESTMO_URL = os.environ.get("TESTMO_URL", "").rstrip("/")
TESTMO_API_KEY = os.environ.get("TESTMO_API_KEY", "")
REQUEST_TIMEOUT = 30.0
UPLOAD_TIMEOUT = 300.0
RATE_LIMIT_DELAY = 0.5
MAX_CASES_PER_REQUEST = 100

# Instance-specific field value mappings.
# Update these to match your Testmo instance. Fetch a few existing cases
# via the API or inspect browser DevTools to discover your IDs.
FIELD_MAPPINGS: dict[str, Any] = {
    "custom_priority": {
        "Critical": 52,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    },
    "custom_type": {
        "Performance": 57,
        "Functional": 59,
        "Usability": 53,
        "Acceptance": 64,
        "Compatibility": 61,
        "Security": 55,
        "Other": 58,
    },
    "custom_creator": {
        "AI Generated": 51,
    },
    "configurations": {
        "Admin Portal": 4,
        "IOS & Android": 5,
        "Insti Web": 10,
    },
    "template_id": {
        "BDD/Gherkin": 4,
        "Steps Table": 1,
    },
    "state_id": {
        "Draft": 1,
        "Review": 2,
        "Approved": 3,
        "Active": 4,
        "Deprecated": 5,
    },
    "status_id": {
        "Incomplete": 1,
        "Complete": 2,
    },
    "result_status_id": {
        "Untested": 1,
        "Passed": 2,
        "Failed": 3,
        "Retest": 4,
        "Blocked": 5,
        "Skipped": 6,
    },
    "automation_run_status": {
        "Success": 2,
        "Failure": 3,
        "Running": 4,
    },
    "custom_issues_tags_and_configurations_added": {
        "Yes": 66,
        "No": 67,
    },
    "tags": {
        "domain": [
            "assets-crypto",
            "assets-noncrypto",
            "services-usergrowth",
            "services-platform",
            "wealth-hnwi",
        ],
        "tier-type": ["ui-verification", "e2e", "negative"],
        "scope": ["regression", "smoke", "sanity"],
        "risk": ["risk-financial", "risk-security", "risk-compliance"],
    },
    "defaults": {
        "template_id": 4,
        "state_id": 1,
        "status_id": 2,
        "custom_priority": 2,
        "custom_type": 59,
        "custom_creator": 51,
        "custom_issues_tags_and_configurations_added": 66,
    },
}


# =============================================================================
# HTTP Client
# =============================================================================


def _get_client() -> httpx.AsyncClient:
    if not TESTMO_URL:
        raise ValueError("TESTMO_URL environment variable not set")
    if not TESTMO_API_KEY:
        raise ValueError("TESTMO_API_KEY environment variable not set")
    return httpx.AsyncClient(
        base_url=f"{TESTMO_URL}/api/v1/",
        headers={
            "Authorization": f"Bearer {TESTMO_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(REQUEST_TIMEOUT),
    
    )


async def _request(
    method: str,
    endpoint: str,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with _get_client() as client:
        response = await client.request(
            method=method,
            url=endpoint,
            json=data,
            params=params,
        )
        if response.status_code == 204:
            return {"success": True}
        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise RuntimeError(
                f"Testmo API error {response.status_code}: "
                f"{json.dumps(error_body) if isinstance(error_body, dict) else error_body}"
            )
        return response.json()


async def _upload(
    endpoint: str,
    files: list[tuple[str, tuple[str, bytes, str]]],
) -> dict[str, Any]:
    """Upload one or more files via multipart form."""
    if not TESTMO_URL or not TESTMO_API_KEY:
        raise ValueError("TESTMO_URL and TESTMO_API_KEY must be set")
    async with httpx.AsyncClient(
        base_url=f"{TESTMO_URL}/api/v1/",
        headers={
            "Authorization": f"Bearer {TESTMO_API_KEY}",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(UPLOAD_TIMEOUT),
    ) as client:
        response = await client.post(endpoint, files=files)
        if response.status_code == 204:
            return {"success": True}
        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise RuntimeError(f"Upload failed {response.status_code}: {error_body}")
        result = response.json()
        return result.get("result", result)


# =============================================================================
# Projects
# =============================================================================


@mcp.tool()
async def testmo_list_projects() -> list[dict[str, Any]]:
    """List all accessible Testmo projects. Returns project IDs, names, and metadata."""
    result = await _request("GET", "/projects")
    return result.get("result", [])


@mcp.tool()
async def testmo_get_project(project_id: int) -> dict[str, Any]:
    """Get details of a specific Testmo project by ID.

    Args:
        project_id: The project ID.
    """
    result = await _request("GET", f"/projects/{project_id}")
    return result.get("result", result)


# =============================================================================
# Folders
# =============================================================================


async def _get_all_folders(project_id: int) -> list[dict[str, Any]]:
    """Fetch all folders with auto-pagination (internal helper)."""
    all_folders: list[dict[str, Any]] = []
    page = 1
    while True:
        result = await _request(
            "GET",
            f"/projects/{project_id}/folders",
            params={"page": page, "per_page": 100},
        )
        all_folders.extend(result.get("result", []))
        if result.get("next_page") is None:
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_folders


def _build_folder_paths(folders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate folders with full_path."""
    folder_map = {f["id"]: f for f in folders}
    for folder in folders:
        path_parts = [folder["name"]]
        parent_id = folder.get("parent_id")
        while parent_id and parent_id in folder_map:
            parent = folder_map[parent_id]
            path_parts.insert(0, parent["name"])
            parent_id = parent.get("parent_id")
        folder["full_path"] = " / ".join(path_parts)
    return folders


@mcp.tool()
async def testmo_list_folders(project_id: int) -> list[dict[str, Any]]:
    """List all folders in a Testmo project with full paths.

    Args:
        project_id: The project ID.
    """
    folders = await _get_all_folders(project_id)
    return _build_folder_paths(folders)


@mcp.tool()
async def testmo_get_folder(project_id: int, folder_id: int) -> dict[str, Any]:
    """Get details of a specific folder.

    Args:
        project_id: The project ID.
        folder_id: The folder ID.
    """
    folders = await _get_all_folders(project_id)
    for folder in folders:
        if folder["id"] == folder_id:
            return folder
    raise RuntimeError(f"Folder {folder_id} not found in project {project_id}")


@mcp.tool()
async def testmo_create_folder(
    project_id: int,
    name: str,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Create a new folder in a Testmo project.

    Args:
        project_id: The project ID.
        name: Folder name.
        parent_id: Parent folder ID (omit for root level).
    """
    folder_data: dict[str, Any] = {"name": name}
    if parent_id:
        folder_data["parent_id"] = parent_id
    result = await _request(
        "POST",
        f"/projects/{project_id}/folders",
        data={"folders": [folder_data]},
    )
    folders = result.get("result", [])
    return folders[0] if folders else result


@mcp.tool()
async def testmo_update_folder(
    project_id: int,
    folder_id: int,
    name: str | None = None,
    parent_id: int | None = None,
    docs: str | None = None,
    display_order: int | None = None,
) -> dict[str, Any]:
    """Update a folder's name, parent, docs, or display order.

    Args:
        project_id: The project ID.
        folder_id: The folder ID to update.
        name: New folder name (optional).
        parent_id: New parent folder ID (optional).
        docs: Docs text for the folder (optional).
        display_order: Display order in UI (optional).
    """
    data: dict[str, Any] = {"ids": [folder_id]}
    if name is not None:
        data["name"] = name
    if parent_id is not None:
        data["parent_id"] = parent_id
    if docs is not None:
        data["docs"] = docs
    if display_order is not None:
        data["display_order"] = display_order
    result = await _request("PATCH", f"/projects/{project_id}/folders", data=data)
    updated = result.get("result", [])
    return updated[0] if updated else result


@mcp.tool()
async def testmo_delete_folder(project_id: int, folder_id: int) -> dict[str, Any]:
    """Delete a folder from a project. WARNING: This also deletes all test cases in the folder.

    Args:
        project_id: The project ID.
        folder_id: The folder ID to delete.
    """
    return await _request(
        "DELETE", f"/projects/{project_id}/folders", data={"ids": [folder_id]}
    )


@mcp.tool()
async def testmo_find_folder_by_name(
    project_id: int,
    name: str,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Find a folder by its name within a project.

    Args:
        project_id: The project ID.
        name: Folder name to search for.
        parent_id: Parent folder ID to search within (omit for root level).
    """
    all_folders = await _get_all_folders(project_id)
    for folder in all_folders:
        folder_parent = folder.get("parent_id") or 0
        search_parent = parent_id or 0
        if folder["name"] == name and folder_parent == search_parent:
            return folder
    return {"found": False, "message": f"Folder '{name}' not found"}


# =============================================================================
# Milestones
# =============================================================================


@mcp.tool()
async def testmo_list_milestones(
    project_id: int,
    is_completed: bool | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List all milestones in a project (e.g., release/5.2.0).

    Args:
        project_id: The project ID.
        is_completed: Filter by completion status (optional).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if is_completed is not None:
        params["is_completed"] = is_completed
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", f"/projects/{project_id}/milestones", params=params)


@mcp.tool()
async def testmo_get_milestone(
    milestone_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific milestone by ID.

    Args:
        milestone_id: The milestone ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET", f"/milestones/{milestone_id}", params=params if params else None
    )
    return result.get("result", result)


# =============================================================================
# Test Cases
# =============================================================================


@mcp.tool()
async def testmo_list_cases(
    project_id: int,
    folder_id: int | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    """List test cases in a project or folder. Supports pagination.

    Args:
        project_id: The project ID.
        folder_id: Filter by folder ID (optional).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if folder_id is not None:
        params["folder_id"] = folder_id
    return await _request("GET", f"/projects/{project_id}/cases", params=params)


@mcp.tool()
async def testmo_get_all_cases(
    project_id: int,
    folder_id: int | None = None,
) -> dict[str, Any]:
    """Get all test cases in a project or folder, handling pagination automatically.

    Args:
        project_id: The project ID.
        folder_id: Folder ID to get cases from (optional).
    """
    all_cases: list[dict[str, Any]] = []
    page = 1
    while True:
        params: dict[str, Any] = {"page": page, "per_page": 100}
        if folder_id is not None:
            params["folder_id"] = folder_id
        result = await _request("GET", f"/projects/{project_id}/cases", params=params)
        all_cases.extend(result.get("result", []))
        if result.get("next_page") is None:
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return {"total": len(all_cases), "cases": all_cases}


@mcp.tool()
async def testmo_get_case(project_id: int, case_id: int) -> dict[str, Any]:
    """Get full details of a specific test case, including custom fields and Gherkin scenarios.

    Args:
        project_id: The project ID.
        case_id: The test case ID.
    """
    page = 1
    while True:
        params: dict[str, Any] = {"page": page, "per_page": 100}
        result = await _request("GET", f"/projects/{project_id}/cases", params=params)
        for case in result.get("result", []):
            if case["id"] == case_id:
                return case
        if result.get("next_page") is None:
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    raise RuntimeError(f"Case {case_id} not found in project {project_id}")


@mcp.tool()
async def testmo_create_case(project_id: int, case_data: dict[str, Any]) -> dict[str, Any]:
    """Create a single test case in Testmo.

    Required fields in case_data:
    - name: Test case title
    - folder_id: Target folder ID (0 for root)
    - custom_priority: Priority ID (52=Critical, 1=High, 2=Medium, 3=Low)
    - custom_type: Type ID (59=Functional, 64=Acceptance, 55=Security)
    - custom_creator: Creator ID (51=AI Generated)

    Optional fields:
    - template_id: 4=BDD/Gherkin (default), 1=Steps Table
    - state_id: 1=Draft, 2=Review, 3=Approved, 4=Active, 5=Deprecated
    - tags: Array of strings
    - issues: Array of issue objects for linking
    - configurations: Platform IDs array (4=Admin Portal, 5=iOS & Android, 10=Insti Web)
    - custom_milestone_id, custom_references, custom_feature, etc.

    Args:
        project_id: The project ID.
        case_data: Test case data object with required fields.
    """
    result = await _request(
        "POST", f"/projects/{project_id}/cases", data={"cases": [case_data]}
    )
    cases = result.get("result", [])
    return cases[0] if cases else result


@mcp.tool()
async def testmo_create_cases(
    project_id: int,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create multiple test cases in a batch (max 100 per call).

    Each case object MUST include these fields or the API will silently reject it:
    - name: Test case title
    - folder_id: Target folder ID (0 for root)
    - custom_priority: Priority ID (52=Critical, 1=High, 2=Medium, 3=Low)
    - custom_type: Type ID (59=Functional, 64=Acceptance, 55=Security)
    - custom_creator: Creator ID (51=AI Generated)

    Optional: template_id, state_id, tags, issues, configurations, custom_feature, etc.

    Args:
        project_id: The project ID.
        cases: Array of test case objects (max 100).
    """
    if len(cases) > MAX_CASES_PER_REQUEST:
        raise ValueError(
            f"Too many cases: {len(cases)}. Max is {MAX_CASES_PER_REQUEST}. "
            "Use testmo_batch_create_cases for larger batches."
        )
    return await _request(
        "POST", f"/projects/{project_id}/cases", data={"cases": cases}
    )


@mcp.tool()
async def testmo_batch_create_cases(
    project_id: int,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create any number of test cases, automatically handling batching (100 per request).

    Each case object MUST include these fields or the API will silently reject it:
    - name: Test case title
    - folder_id: Target folder ID (0 for root)
    - custom_priority: Priority ID (52=Critical, 1=High, 2=Medium, 3=Low)
    - custom_type: Type ID (59=Functional, 64=Acceptance, 55=Security)
    - custom_creator: Creator ID (51=AI Generated)

    Optional: template_id, state_id, tags, issues, configurations, custom_feature, etc.

    Args:
        project_id: The project ID.
        cases: Array of test case objects (unlimited, auto-batched).
    """
    all_created: list[dict[str, Any]] = []
    errors: list[str] = []

    for i in range(0, len(cases), MAX_CASES_PER_REQUEST):
        batch = cases[i : i + MAX_CASES_PER_REQUEST]
        batch_num = (i // MAX_CASES_PER_REQUEST) + 1
        try:
            result = await _request(
                "POST", f"/projects/{project_id}/cases", data={"cases": batch}
            )
            all_created.extend(result.get("result", []))
        except RuntimeError as e:
            errors.append(f"Batch {batch_num}: {e}")

        if i + MAX_CASES_PER_REQUEST < len(cases):
            await asyncio.sleep(RATE_LIMIT_DELAY)

    return {
        "result": all_created,
        "total_submitted": len(cases),
        "total_created": len(all_created),
        "errors": errors if errors else None,
    }


@mcp.tool()
async def testmo_update_case(
    project_id: int,
    case_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing test case. Only include fields you want to change.

    Issue Linking: Use issues array with objects like
    {"display_id": "PROJ-123", "integration_id": 1, "connection_project_id": "org/repo"}.
    Use testmo_list_issue_connections to discover integration_id values.

    Args:
        project_id: The project ID.
        case_id: The test case ID to update.
        data: Fields to update.
    """
    payload: dict[str, Any] = {"ids": [case_id]}
    payload.update(data)
    result = await _request("PATCH", f"/projects/{project_id}/cases", data=payload)
    cases = result.get("result", result)
    if isinstance(cases, list) and len(cases) == 1:
        return cases[0]
    return cases


@mcp.tool()
async def testmo_batch_update_cases(
    project_id: int,
    ids: list[int],
    folder_id: int | None = None,
    state_id: int | None = None,
    status_id: int | None = None,
    estimate: int | None = None,
    custom_priority: int | None = None,
    automation_links: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bulk update up to 100 test cases with the same field values (PATCH).

    Useful for moving cases to a folder, updating priority/state in bulk,
    linking automation sources, or adding tags/issues to multiple cases.

    Args:
        project_id: The project ID.
        ids: Array of case IDs to update (max 100).
        folder_id: Target folder ID.
        state_id: State ID (1=Draft, 2=Review, 3=Approved, 4=Active, 5=Deprecated).
        status_id: Status ID.
        estimate: Estimated execution duration.
        custom_priority: Priority ID (52=Critical, 1=High, 2=Medium, 3=Low).
        automation_links: Automation links (automation_source_id, automation_case_id, name).
        tags: Tags to apply.
        issues: Issue links (display_id, integration_id, connection_project_id).
    """
    payload: dict[str, Any] = {"ids": ids}
    if folder_id is not None:
        payload["folder_id"] = folder_id
    if state_id is not None:
        payload["state_id"] = state_id
    if status_id is not None:
        payload["status_id"] = status_id
    if estimate is not None:
        payload["estimate"] = estimate
    if custom_priority is not None:
        payload["custom_priority"] = custom_priority
    if automation_links is not None:
        payload["automation_links"] = automation_links
    if tags is not None:
        payload["tags"] = tags
    if issues is not None:
        payload["issues"] = issues
    result = await _request("PATCH", f"/projects/{project_id}/cases", data=payload)
    updated = result.get("result", [])
    return {"result": updated, "total_updated": len(updated)}


@mcp.tool()
async def testmo_delete_case(project_id: int, case_id: int) -> dict[str, Any]:
    """Delete a test case.

    Args:
        project_id: The project ID.
        case_id: The test case ID to delete.
    """
    return await _request(
        "DELETE", f"/projects/{project_id}/cases", data={"ids": [case_id]}
    )


@mcp.tool()
async def testmo_batch_delete_cases(
    project_id: int,
    case_ids: list[int],
) -> dict[str, Any]:
    """Delete multiple test cases (max 100 per call).

    Args:
        project_id: The project ID.
        case_ids: Array of test case IDs to delete (max 100).
    """
    if len(case_ids) > MAX_CASES_PER_REQUEST:
        all_errors: list[str] = []
        total_deleted = 0
        for i in range(0, len(case_ids), MAX_CASES_PER_REQUEST):
            batch = case_ids[i : i + MAX_CASES_PER_REQUEST]
            batch_num = (i // MAX_CASES_PER_REQUEST) + 1
            try:
                await _request(
                    "DELETE", f"/projects/{project_id}/cases", data={"ids": batch}
                )
                total_deleted += len(batch)
            except RuntimeError as e:
                all_errors.append(f"Batch {batch_num}: {e}")
            if i + MAX_CASES_PER_REQUEST < len(case_ids):
                await asyncio.sleep(RATE_LIMIT_DELAY)
        return {
            "total_requested": len(case_ids),
            "total_deleted": total_deleted,
            "errors": all_errors if all_errors else None,
        }
    return await _request(
        "DELETE", f"/projects/{project_id}/cases", data={"ids": case_ids}
    )


@mcp.tool()
async def testmo_search_cases(
    project_id: int,
    query: str | None = None,
    folder_id: int | None = None,
    tags: list[str] | None = None,
    state_id: int | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    """Search for test cases with filters (query, folder, tags, state).

    Args:
        project_id: The project ID.
        query: Search query (searches name and description).
        folder_id: Filter by folder ID.
        tags: Filter by tags.
        state_id: Filter by state (1=Draft, 2=Review, 3=Approved, 4=Active, 5=Deprecated).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if query:
        params["query"] = query
    if folder_id is not None:
        params["folder_id"] = folder_id
    if tags:
        params["tags"] = ",".join(tags)
    if state_id is not None:
        params["state_id"] = state_id
    return await _request("GET", f"/projects/{project_id}/cases", params=params)


# =============================================================================
# Test Runs
# =============================================================================


@mcp.tool()
async def testmo_list_runs(
    project_id: int,
    page: int = 1,
    per_page: int = 100,
    is_closed: bool | None = None,
    milestone_id: str | None = None,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List test runs in a project.

    Args:
        project_id: The project ID.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        is_closed: Filter by closed status.
        milestone_id: Comma-separated milestone IDs to filter by.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if is_closed is not None:
        params["is_closed"] = is_closed
    if milestone_id:
        params["milestone_id"] = milestone_id
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", f"/projects/{project_id}/runs", params=params)


@mcp.tool()
async def testmo_get_run(
    run_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific test run.

    Args:
        run_id: The test run ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request("GET", f"/runs/{run_id}", params=params if params else None)
    return result.get("result", result)


# =============================================================================
# Run Results
# =============================================================================


@mcp.tool()
async def testmo_list_run_results(
    run_id: int,
    status_id: str | None = None,
    assignee_id: str | None = None,
    created_by: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    get_latest_result: bool | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List test results for a run with optional filters.

    Args:
        run_id: The test run ID.
        status_id: Comma-separated status IDs (1=Untested, 2=Passed, 3=Failed, 4=Retest, 5=Blocked, 6=Skipped).
        assignee_id: Comma-separated assignee IDs.
        created_by: Comma-separated user IDs who created results.
        created_after: Filter results created after (ISO8601 format).
        created_before: Filter results created before (ISO8601 format).
        get_latest_result: If true, return only the latest result per test.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if status_id:
        params["status_id"] = status_id
    if assignee_id:
        params["assignee_id"] = assignee_id
    if created_by:
        params["created_by"] = created_by
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if get_latest_result is not None:
        params["get_latest_result"] = get_latest_result
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", f"/runs/{run_id}/results", params=params)


# =============================================================================
# Case Attachments
# =============================================================================


@mcp.tool()
async def testmo_list_case_attachments(
    case_id: int,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List all attachments for a test case.

    Args:
        case_id: The test case ID.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", f"/cases/{case_id}/attachments", params=params)


MAX_IMAGE_SIZE = 1_000_000  # 1 MB — compress images larger than this
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def _prepare_file(file_path: str) -> tuple[str, bytes, str]:
    """Read a file and compress it if it's a large image. Returns (filename, content, content_type)."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    file_content = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS and len(file_content) > MAX_IMAGE_SIZE:
        img = Image.open(io.BytesIO(file_content))
        img = img.convert("RGB")
        buf = io.BytesIO()
        quality = 85
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        while buf.tell() > MAX_IMAGE_SIZE and quality > 20:
            quality -= 10
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        file_content = buf.getvalue()
        filename = path.stem + ".jpg"
        content_type = "image/jpeg"
    else:
        filename = path.name
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return filename, file_content, content_type


@mcp.tool()
async def testmo_upload_case_attachment(
    case_id: int,
    file_path: str,
) -> dict[str, Any]:
    """Upload a single file attachment to a test case. Large images are auto-compressed.

    IMPORTANT: file_path must be an absolute path to a file saved on disk (e.g. /Users/jan/Desktop/screenshot.png).
    Pasted images or image data from the conversation cannot be uploaded — the user must save the file first and provide its path.
    If no path is provided or the user has not saved the file yet, ask them to save it and share the full file path.

    Args:
        case_id: The test case ID.
        file_path: Absolute path to the local file to upload (e.g. /Users/jan/Desktop/screenshot.png).
    """
    if not file_path or not file_path.strip():
        raise ValueError("file_path is required. Ask the user to save the file to disk and provide the full path (e.g. /Users/jan/Desktop/screenshot.png).")
    filename, file_content, content_type = _prepare_file(file_path)
    return await _upload(
        f"/cases/{case_id}/attachments/single",
        [("file", (filename, file_content, content_type))],
    )


@mcp.tool()
async def testmo_upload_case_attachments(
    case_id: int,
    file_paths: list[str],
) -> dict[str, Any]:
    """Upload up to 20 file attachments to a test case in one request. Large images are auto-compressed.

    IMPORTANT: Each path must be an absolute path to a file saved on disk.
    Pasted images or image data from the conversation cannot be uploaded — the user must save the files first.
    If no paths are provided, ask the user to save the files and share their full paths.

    Args:
        case_id: The test case ID.
        file_paths: List of absolute paths to local files to upload (max 20).
    """
    if not file_paths:
        raise ValueError("file_paths must not be empty")
    if len(file_paths) > 20:
        file_paths = file_paths[:20]
    files = []
    for fp in file_paths:
        filename, file_content, content_type = _prepare_file(fp)
        files.append(("file", (filename, file_content, content_type)))
    return await _upload(f"/cases/{case_id}/attachments", files)


@mcp.tool()
async def testmo_delete_case_attachments(
    case_id: int,
    attachment_ids: list[int],
) -> dict[str, Any]:
    """Delete one or more attachments from a test case.

    Args:
        case_id: The test case ID.
        attachment_ids: Array of attachment IDs to delete.
    """
    return await _request(
        "DELETE", f"/cases/{case_id}/attachments", data={"ids": attachment_ids}
    )


# =============================================================================
# Automation Sources
# =============================================================================


@mcp.tool()
async def testmo_list_automation_sources(
    project_id: int,
    is_retired: bool | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List automation sources in a project (CI/CD integrations).

    Args:
        project_id: The project ID.
        is_retired: Filter by retired status (optional).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if is_retired is not None:
        params["is_retired"] = is_retired
    if expands:
        params["expands"] = ",".join(expands)
    return await _request(
        "GET", f"/projects/{project_id}/automation/sources", params=params
    )


@mcp.tool()
async def testmo_get_automation_source(
    automation_source_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific automation source.

    Args:
        automation_source_id: The automation source ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET",
        f"/automation/sources/{automation_source_id}",
        params=params if params else None,
    )
    return result.get("result", result)


# =============================================================================
# Automation Runs
# =============================================================================


@mcp.tool()
async def testmo_list_automation_runs(
    project_id: int,
    source_id: str | None = None,
    milestone_id: str | None = None,
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    tags: str | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List automation runs in a project with optional filters.

    Args:
        project_id: The project ID.
        source_id: Comma-separated automation source IDs to filter by.
        milestone_id: Comma-separated milestone IDs to filter by.
        status: Comma-separated status values (2=Success, 3=Failure, 4=Running).
        created_after: Filter runs created after (ISO8601 format).
        created_before: Filter runs created before (ISO8601 format).
        tags: Comma-separated tags to filter by.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if source_id:
        params["source_id"] = source_id
    if milestone_id:
        params["milestone_id"] = milestone_id
    if status:
        params["status"] = status
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if tags:
        params["tags"] = tags
    if expands:
        params["expands"] = ",".join(expands)
    return await _request(
        "GET", f"/projects/{project_id}/automation/runs", params=params
    )


@mcp.tool()
async def testmo_get_automation_run(
    automation_run_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific automation run.

    Args:
        automation_run_id: The automation run ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET",
        f"/automation/runs/{automation_run_id}",
        params=params if params else None,
    )
    return result.get("result", result)


@mcp.tool()
async def testmo_create_automation_run(
    project_id: int,
    name: str,
    source: str,
    config: str | None = None,
    config_id: int | None = None,
    milestone: str | None = None,
    milestone_id: int | None = None,
    tags: list[str] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new automation run in a project.

    The source name identifies the CI/CD integration (e.g., 'frontend', 'backend').
    If the source doesn't exist, Testmo auto-creates it.

    Args:
        project_id: The target project ID.
        name: Name of the automation run.
        source: Automation source name (auto-created if new).
        config: Configuration name (optional).
        config_id: Configuration ID (takes precedence over config).
        milestone: Milestone name (optional).
        milestone_id: Milestone ID (takes precedence over milestone).
        tags: Tags for the run (matching automation tags on milestones auto-link the run).
        artifacts: External test artifacts [{name, url, mime_type?, size?}].
        fields: Custom fields [{name, type, value}].
        links: Links [{name, url}] (e.g., back to CI build).
    """
    data: dict[str, Any] = {"name": name, "source": source}
    if config is not None:
        data["config"] = config
    if config_id is not None:
        data["config_id"] = config_id
    if milestone is not None:
        data["milestone"] = milestone
    if milestone_id is not None:
        data["milestone_id"] = milestone_id
    if tags:
        data["tags"] = tags
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if links:
        data["links"] = links
    return await _request("POST", f"/projects/{project_id}/automation/runs", data=data)


@mcp.tool()
async def testmo_append_automation_run(
    automation_run_id: int,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append test artifacts, fields, or links to an existing automation run.

    Args:
        automation_run_id: The automation run ID.
        artifacts: External test artifacts to append.
        fields: Custom fields to append.
        links: Links to append.
    """
    data: dict[str, Any] = {}
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if links:
        data["links"] = links
    return await _request(
        "POST", f"/automation/runs/{automation_run_id}/append", data=data
    )


@mcp.tool()
async def testmo_complete_automation_run(
    automation_run_id: int,
    measure_elapsed: bool | None = None,
) -> dict[str, Any]:
    """Mark an automation run as completed.

    Args:
        automation_run_id: The automation run ID to complete.
        measure_elapsed: Auto-set execution time from creation to completion.
    """
    data: dict[str, Any] = {}
    if measure_elapsed is not None:
        data["measure_elapsed"] = measure_elapsed
    return await _request(
        "POST",
        f"/automation/runs/{automation_run_id}/complete",
        data=data if data else None,
    )


@mcp.tool()
async def testmo_create_automation_run_thread(
    automation_run_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new thread in an automation run for submitting test results.

    Threads represent parallel test execution lanes. After creating, use
    testmo_append_automation_run_thread to submit test results.

    Args:
        automation_run_id: The automation run ID.
        elapsed_observed: Observed execution time in microseconds.
        elapsed_computed: Computed execution time in microseconds.
        artifacts: External test artifacts for the thread.
        fields: Custom fields for the thread.
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    return await _request(
        "POST",
        f"/automation/runs/{automation_run_id}/threads",
        data=data if data else None,
    )


@mcp.tool()
async def testmo_append_automation_run_thread(
    thread_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    tests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append test results, artifacts, or fields to an automation run thread.

    Each test in the 'tests' array: {key, name, folder, status, elapsed, file, line, assertions, artifacts, fields}.
    Status values: 'passed', 'failed', 'skipped', etc.

    Args:
        thread_id: The automation run thread ID.
        elapsed_observed: Partial observed time in microseconds to add.
        elapsed_computed: Partial computed time in microseconds to add.
        artifacts: External test artifacts to append.
        fields: Custom fields to append.
        tests: Test results to submit [{name, status, ...}].
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if tests:
        data["tests"] = tests
    return await _request(
        "POST", f"/automation/runs/threads/{thread_id}/append", data=data
    )


@mcp.tool()
async def testmo_complete_automation_run_thread(
    thread_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
) -> dict[str, Any]:
    """Mark an automation run thread as completed.

    Args:
        thread_id: The automation run thread ID to complete.
        elapsed_observed: Observed execution time in microseconds.
        elapsed_computed: Computed execution time in microseconds.
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    return await _request(
        "POST",
        f"/automation/runs/threads/{thread_id}/complete",
        data=data if data else None,
    )


# =============================================================================
# Issue Connections
# =============================================================================


@mcp.tool()
async def testmo_list_issue_connections(
    project_id: int | None = None,
    integration_type: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List available issue integrations (GitHub, Jira, Azure DevOps, etc.).

    Discover configured issue tracker integrations. Returns integration_id and
    connection_project_id needed for linking issues to test cases.

    Args:
        project_id: Filter by project ID (optional).
        integration_type: Filter by type (e.g., 'github', 'jira', 'azure_devops').
        is_active: Filter by active status (optional).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if project_id is not None:
        params["project_id"] = project_id
    if integration_type:
        params["integration_type"] = integration_type
    if is_active is not None:
        params["is_active"] = is_active
    if expands:
        params["expands"] = ",".join(expands)
    return await _request("GET", "/issues/connections", params=params)


@mcp.tool()
async def testmo_get_issue_connection(
    connection_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific issue connection.

    Args:
        connection_id: The issue connection ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET",
        f"/issues/connections/{connection_id}",
        params=params if params else None,
    )
    return result.get("result", result)


# =============================================================================
# Composite / Recursive Operations
# =============================================================================


def _collect_subtree(all_folders: list[dict[str, Any]], root_id: int) -> set[int]:
    """Return set of folder IDs in the subtree rooted at root_id (inclusive)."""
    children_map: dict[int, list[int]] = defaultdict(list)
    for f in all_folders:
        children_map[f.get("parent_id") or 0].append(f["id"])
    result = {root_id}
    stack = [root_id]
    while stack:
        current = stack.pop()
        for child_id in children_map.get(current, []):
            result.add(child_id)
            stack.append(child_id)
    return result


def _build_folder_map(all_folders: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {f["id"]: f for f in all_folders}


def _get_folder_path(folder_id: int, folder_map: dict[int, dict[str, Any]]) -> str:
    if folder_id not in folder_map:
        return ""
    folder = folder_map[folder_id]
    path_parts = [folder["name"]]
    parent_id = folder.get("parent_id")
    while parent_id and parent_id in folder_map:
        parent = folder_map[parent_id]
        path_parts.insert(0, parent["name"])
        parent_id = parent.get("parent_id")
    return " / ".join(path_parts)


def _build_folder_tree(
    all_folders: list[dict[str, Any]],
    subtree_ids: set[int],
    root_id: int,
    folder_map: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    children_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for f in all_folders:
        if f["id"] not in subtree_ids:
            continue
        children_map[f.get("parent_id") or 0].append(f)

    def build_node(folder: dict[str, Any]) -> dict[str, Any]:
        node = {**folder}
        node["full_path"] = _get_folder_path(folder["id"], folder_map)
        node["children"] = [
            build_node(child) for child in children_map.get(folder["id"], [])
        ]
        return node

    if root_id not in folder_map:
        return None
    return build_node(folder_map[root_id])


async def _search_paginated(
    project_id: int,
    query: str | None,
    folder_id: int | None,
    tags: list[str] | None,
    state_id: int | None,
    expands: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Auto-paginate search_cases results."""
    all_cases: list[dict[str, Any]] = []
    page = 1
    while True:
        params: dict[str, Any] = {"page": page, "per_page": 100}
        if query:
            params["query"] = query
        if folder_id is not None:
            params["folder_id"] = folder_id
        if tags:
            params["tags"] = ",".join(tags)
        if state_id is not None:
            params["state_id"] = state_id
        if expands:
            params["expands"] = ",".join(expands)
        result = await _request("GET", f"/projects/{project_id}/cases", params=params)
        all_cases.extend(result.get("result", []))
        if result.get("next_page") is None:
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return all_cases


def _apply_client_filters(
    cases: list[dict[str, Any]],
    custom_filters: dict[str, Any] | None,
    match_mode: str,
    array_filters: dict[str, list[Any]] | None,
    issue_key: str | None,
    tags_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    result = cases

    if tags_filter:
        tag_set = set(tags_filter)
        def _match_tags(case: dict[str, Any]) -> bool:
            case_tag_names = {
                t["name"] for t in case.get("tags", []) if isinstance(t, dict)
            }
            return bool(case_tag_names & tag_set)
        result = [c for c in result if _match_tags(c)]

    if custom_filters:
        def _match(case: dict[str, Any]) -> bool:
            for k, v in custom_filters.items():
                case_val = case.get(k)
                if match_mode == "contains" and isinstance(v, str):
                    if not isinstance(case_val, str) or v.lower() not in case_val.lower():
                        return False
                elif case_val != v:
                    return False
            return True
        result = [c for c in result if _match(c)]

    if array_filters:
        def _match_arr(case: dict[str, Any]) -> bool:
            for k, filter_vals in array_filters.items():
                case_arr = case.get(k)
                if not isinstance(case_arr, list):
                    return False
                if not any(fv in case_arr for fv in filter_vals):
                    return False
            return True
        result = [c for c in result if _match_arr(c)]

    if issue_key:
        def _match_issue(case: dict[str, Any]) -> bool:
            issues = case.get("issues", [])
            if not isinstance(issues, list):
                return False
            return any(
                iss.get("display_id") == issue_key
                for iss in issues
                if isinstance(iss, dict)
            )
        result = [c for c in result if _match_issue(c)]

    return result


@mcp.tool()
async def testmo_get_folders_recursive(
    project_id: int,
    folder_id: int,
) -> dict[str, Any]:
    """Get a folder and all descendant subfolders as a nested tree in a single call.

    Args:
        project_id: The project ID.
        folder_id: The root folder ID to start recursion from.
    """
    all_folders = await _get_all_folders(project_id)
    folder_map = _build_folder_map(all_folders)
    if folder_id not in folder_map:
        return {"error": f"Folder {folder_id} not found in project {project_id}"}
    subtree_ids = _collect_subtree(all_folders, folder_id)
    tree = _build_folder_tree(all_folders, subtree_ids, folder_id, folder_map)
    return {"total_folders": len(subtree_ids), "tree": tree}


@mcp.tool()
async def testmo_get_cases_recursive(
    project_id: int,
    folder_id: int,
    include_folder_path: bool = True,
) -> dict[str, Any]:
    """Get all test cases from a folder and all subfolders in a single call.

    Returns a flat list of cases annotated with folder name/path, plus per-folder counts.

    Args:
        project_id: The project ID.
        folder_id: The root folder ID to collect cases from recursively.
        include_folder_path: Include folder path on each case (default: true).
    """
    all_folders = await _get_all_folders(project_id)
    folder_map = _build_folder_map(all_folders)
    if folder_id not in folder_map:
        return {"error": f"Folder {folder_id} not found in project {project_id}"}

    subtree_ids = _collect_subtree(all_folders, folder_id)
    all_cases: list[dict[str, Any]] = []
    folder_summary: list[dict[str, Any]] = []

    for fid in sorted(subtree_ids):
        cases_page: list[dict[str, Any]] = []
        page = 1
        while True:
            params: dict[str, Any] = {"page": page, "per_page": 100, "folder_id": fid}
            result = await _request(
                "GET", f"/projects/{project_id}/cases", params=params
            )
            cases_page.extend(result.get("result", []))
            if result.get("next_page") is None:
                break
            page += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)

        folder_name = folder_map[fid]["name"] if fid in folder_map else str(fid)
        folder_path = _get_folder_path(fid, folder_map) if include_folder_path else None

        if cases_page:
            folder_summary.append({
                "folder_id": fid,
                "folder_name": folder_name,
                "folder_path": folder_path,
                "case_count": len(cases_page),
            })

        for case in cases_page:
            case["_folder_name"] = folder_name
            if include_folder_path:
                case["_folder_path"] = folder_path
            all_cases.append(case)

        if len(subtree_ids) > 1:
            await asyncio.sleep(RATE_LIMIT_DELAY)

    return {
        "total_cases": len(all_cases),
        "total_folders_searched": len(subtree_ids),
        "folder_summary": folder_summary,
        "cases": all_cases,
    }


@mcp.tool()
async def testmo_search_cases_recursive(
    project_id: int,
    folder_id: int | None = None,
    query: str | None = None,
    tags: list[str] | None = None,
    state_id: int | None = None,
    custom_filters: dict[str, Any] | None = None,
    match_mode: str = "exact",
    array_filters: dict[str, list[Any]] | None = None,
    issue_key: str | None = None,
) -> dict[str, Any]:
    """Search test cases recursively within a folder subtree or project-wide.

    Supports API-level filters (query, tags, state_id) plus client-side filters:
    - custom_filters: match case properties (exact or contains mode)
    - array_filters: match cases where array fields contain ANY of given values
    - issue_key: match cases linked to a specific issue (e.g., Jira key)

    Args:
        project_id: The project ID.
        folder_id: Root folder to search within (omit for project-wide search).
        query: Search query (searches name and description).
        tags: Filter by tags (API-level).
        state_id: Filter by state (1=Draft, 2=Review, 3=Approved, 4=Active, 5=Deprecated).
        custom_filters: Key-value pairs to match on case properties.
        match_mode: 'exact' or 'contains' for string values in custom_filters.
        array_filters: Key-value pairs where value is list, matches if ANY value present.
        issue_key: Match cases linked to this issue (checks issues[].display_id).
    """
    all_folders = await _get_all_folders(project_id)
    folder_map = _build_folder_map(all_folders)

    if folder_id is not None:
        if folder_id not in folder_map:
            return {"error": f"Folder {folder_id} not found in project {project_id}"}
        subtree_ids: set[int] | None = _collect_subtree(all_folders, folder_id)
    else:
        subtree_ids = None

    has_client_filters = bool(custom_filters or array_filters or issue_key)
    all_matches: list[dict[str, Any]] = []
    folder_summary: list[dict[str, Any]] = []

    if subtree_ids is not None:
        for fid in sorted(subtree_ids):
            folder_cases = await _search_paginated(
                project_id, query, fid, tags, state_id
            )
            if has_client_filters:
                folder_cases = _apply_client_filters(
                    folder_cases, custom_filters, match_mode, array_filters, issue_key
                )
            folder_name = folder_map[fid]["name"] if fid in folder_map else str(fid)
            folder_path = _get_folder_path(fid, folder_map)
            if folder_cases:
                folder_summary.append({
                    "folder_id": fid,
                    "folder_name": folder_name,
                    "folder_path": folder_path,
                    "match_count": len(folder_cases),
                })
            for case in folder_cases:
                case["_folder_name"] = folder_name
                case["_folder_path"] = folder_path
                all_matches.append(case)
            if len(subtree_ids) > 1:
                await asyncio.sleep(RATE_LIMIT_DELAY)
    else:
        all_cases = await _search_paginated(project_id, query, None, tags, state_id)
        if has_client_filters:
            all_cases = _apply_client_filters(
                all_cases, custom_filters, match_mode, array_filters, issue_key
            )
        for case in all_cases:
            cfid = case.get("folder_id")
            if cfid and cfid in folder_map:
                case["_folder_name"] = folder_map[cfid]["name"]
                case["_folder_path"] = _get_folder_path(cfid, folder_map)
            else:
                case["_folder_name"] = str(cfid) if cfid else "root"
                case["_folder_path"] = ""
            all_matches.append(case)
        folder_counts: dict[int, int] = defaultdict(int)
        for case in all_matches:
            folder_counts[case.get("folder_id", 0)] += 1
        for fid_key, count in sorted(folder_counts.items()):
            folder_summary.append({
                "folder_id": fid_key,
                "folder_name": (
                    folder_map[fid_key]["name"] if fid_key in folder_map else str(fid_key)
                ),
                "folder_path": _get_folder_path(fid_key, folder_map),
                "match_count": count,
            })

    return {
        "total_matches": len(all_matches),
        "total_folders_searched": (
            len(subtree_ids) if subtree_ids is not None else len(all_folders)
        ),
        "folder_summary": folder_summary,
        "cases": all_matches,
    }


# =============================================================================
# Utility
# =============================================================================


@mcp.tool()
async def testmo_get_field_mappings() -> dict[str, Any]:
    """Get the field value mappings for this Testmo instance.

    Returns mappings for: custom_priority, custom_type, configurations,
    state_id, result_status_id, automation_run_status, tags, and defaults.
    Use this to look up correct numeric IDs before creating/updating test cases.
    """
    return FIELD_MAPPINGS


@mcp.tool()
async def testmo_get_web_url(
    project_id: int,
    resource_type: str = "repositories",
    resource_id: int | None = None,
) -> dict[str, str]:
    """Generate a web URL for viewing a resource in Testmo.

    Args:
        project_id: The project ID.
        resource_type: Type of resource (repositories, runs).
        resource_id: Resource ID (e.g., folder ID).
    """
    url = f"{TESTMO_URL}/{resource_type}/{project_id}"
    if resource_id:
        url += f"?group_id={resource_id}"
    return {"url": url}


# =============================================================================
# Entry Point
# =============================================================================


if __name__ == "__main__":
    mcp.run(transport="stdio")
