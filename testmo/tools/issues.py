from typing import Any

from ..server import mcp
from ..client import _request


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
