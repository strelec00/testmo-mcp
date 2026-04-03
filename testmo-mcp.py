import asyncio
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("testmo-mcp")

TESTMO_URL = os.environ.get("TESTMO_URL", "").rstrip("/")
TESTMO_API_KEY = os.environ.get("TESTMO_API_KEY", "")
REQUEST_TIMEOUT = 30.0
RATE_LIMIT_DELAY = 0.5


def _get_client() -> httpx.AsyncClient:
    if not TESTMO_URL:
        raise ValueError("TESTMO_URL environment variable not set")
    if not TESTMO_API_KEY:
        raise ValueError("TESTMO_API_KEY environment variable not set")
    return httpx.AsyncClient(
        base_url=f"{TESTMO_URL}/api/v1",
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
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async with _get_client() as client:
        response = await client.request(method=method, url=endpoint, params=params)
        if response.status_code >= 400:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise RuntimeError(
                f"Testmo API error {response.status_code}: {error_body}"
            )
        return response.json()


@mcp.tool()
async def list_cases(
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
        per_page: Results per page — 25, 50, or 100 (default: 100).
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if folder_id is not None:
        params["folder_id"] = folder_id
    return await _request("GET", f"/projects/{project_id}/cases", params=params)


@mcp.tool()
async def get_all_cases(
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
        cases = result.get("result", [])
        all_cases.extend(cases)
        if result.get("next_page") is None:
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return {"total": len(all_cases), "cases": all_cases}


@mcp.tool()
async def get_case(project_id: int, case_id: int) -> dict[str, Any]:
    """Get full details of a specific test case, including custom fields and Gherkin scenarios.

    Args:
        project_id: The project ID.
        case_id: The test case ID.
    """
    result = await _request("GET", f"/projects/{project_id}/cases/{case_id}")
    return result.get("result", result)


@mcp.tool()
async def search_cases(
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
        folder_id: Filter by folder ID (optional).
        tags: Filter by tags (optional).
        state_id: Filter by state — 1=Draft, 2=Review, 3=Approved, 4=Active, 5=Deprecated (optional).
        page: Page number (default: 1).
        per_page: Results per page — 25, 50, or 100 (default: 100).
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
