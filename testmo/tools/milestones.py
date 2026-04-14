from typing import Any

from ..server import mcp
from ..client import _request


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
