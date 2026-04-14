import json
from typing import Any

import httpx

from .config import TESTMO_URL, TESTMO_API_KEY, REQUEST_TIMEOUT, UPLOAD_TIMEOUT


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
