from typing import Any

from ..server import mcp
from ..client import _request


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
