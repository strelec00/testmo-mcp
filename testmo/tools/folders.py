import asyncio
from typing import Any

from ..server import mcp
from ..client import _request
from ..config import RATE_LIMIT_DELAY


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
