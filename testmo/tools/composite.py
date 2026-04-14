import asyncio
from collections import defaultdict
from typing import Any

from ..server import mcp
from ..client import _request
from ..config import RATE_LIMIT_DELAY
from .folders import _get_all_folders


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
