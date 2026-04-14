from typing import Any

from ..server import mcp
from ..client import _request


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
