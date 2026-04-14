from typing import Any

from ..server import mcp
from ..config import FIELD_MAPPINGS, TESTMO_URL


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
