import asyncio
from typing import Any

from ..server import mcp
from ..client import _request
from ..config import RATE_LIMIT_DELAY, MAX_CASES_PER_REQUEST


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
