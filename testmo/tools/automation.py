from typing import Any

from ..server import mcp
from ..client import _request


@mcp.tool()
async def testmo_list_automation_sources(
    project_id: int,
    is_retired: bool | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List automation sources in a project (CI/CD integrations).

    Args:
        project_id: The project ID.
        is_retired: Filter by retired status (optional).
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if is_retired is not None:
        params["is_retired"] = is_retired
    if expands:
        params["expands"] = ",".join(expands)
    return await _request(
        "GET", f"/projects/{project_id}/automation/sources", params=params
    )


@mcp.tool()
async def testmo_get_automation_source(
    automation_source_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific automation source.

    Args:
        automation_source_id: The automation source ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET",
        f"/automation/sources/{automation_source_id}",
        params=params if params else None,
    )
    return result.get("result", result)


@mcp.tool()
async def testmo_list_automation_runs(
    project_id: int,
    source_id: str | None = None,
    milestone_id: str | None = None,
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    tags: str | None = None,
    page: int = 1,
    per_page: int = 100,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """List automation runs in a project with optional filters.

    Args:
        project_id: The project ID.
        source_id: Comma-separated automation source IDs to filter by.
        milestone_id: Comma-separated milestone IDs to filter by.
        status: Comma-separated status values (2=Success, 3=Failure, 4=Running).
        created_after: Filter runs created after (ISO8601 format).
        created_before: Filter runs created before (ISO8601 format).
        tags: Comma-separated tags to filter by.
        page: Page number (default: 1).
        per_page: Results per page (default: 100). Valid: 25, 50, 100.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if source_id:
        params["source_id"] = source_id
    if milestone_id:
        params["milestone_id"] = milestone_id
    if status:
        params["status"] = status
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if tags:
        params["tags"] = tags
    if expands:
        params["expands"] = ",".join(expands)
    return await _request(
        "GET", f"/projects/{project_id}/automation/runs", params=params
    )


@mcp.tool()
async def testmo_get_automation_run(
    automation_run_id: int,
    expands: list[str] | None = None,
) -> dict[str, Any]:
    """Get details of a specific automation run.

    Args:
        automation_run_id: The automation run ID.
        expands: Related entities to include.
    """
    params: dict[str, Any] = {}
    if expands:
        params["expands"] = ",".join(expands)
    result = await _request(
        "GET",
        f"/automation/runs/{automation_run_id}",
        params=params if params else None,
    )
    return result.get("result", result)


@mcp.tool()
async def testmo_create_automation_run(
    project_id: int,
    name: str,
    source: str,
    config: str | None = None,
    config_id: int | None = None,
    milestone: str | None = None,
    milestone_id: int | None = None,
    tags: list[str] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new automation run in a project.

    The source name identifies the CI/CD integration (e.g., 'frontend', 'backend').
    If the source doesn't exist, Testmo auto-creates it.

    Args:
        project_id: The target project ID.
        name: Name of the automation run.
        source: Automation source name (auto-created if new).
        config: Configuration name (optional).
        config_id: Configuration ID (takes precedence over config).
        milestone: Milestone name (optional).
        milestone_id: Milestone ID (takes precedence over milestone).
        tags: Tags for the run (matching automation tags on milestones auto-link the run).
        artifacts: External test artifacts [{name, url, mime_type?, size?}].
        fields: Custom fields [{name, type, value}].
        links: Links [{name, url}] (e.g., back to CI build).
    """
    data: dict[str, Any] = {"name": name, "source": source}
    if config is not None:
        data["config"] = config
    if config_id is not None:
        data["config_id"] = config_id
    if milestone is not None:
        data["milestone"] = milestone
    if milestone_id is not None:
        data["milestone_id"] = milestone_id
    if tags:
        data["tags"] = tags
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if links:
        data["links"] = links
    return await _request("POST", f"/projects/{project_id}/automation/runs", data=data)


@mcp.tool()
async def testmo_append_automation_run(
    automation_run_id: int,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append test artifacts, fields, or links to an existing automation run.

    Args:
        automation_run_id: The automation run ID.
        artifacts: External test artifacts to append.
        fields: Custom fields to append.
        links: Links to append.
    """
    data: dict[str, Any] = {}
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if links:
        data["links"] = links
    return await _request(
        "POST", f"/automation/runs/{automation_run_id}/append", data=data
    )


@mcp.tool()
async def testmo_complete_automation_run(
    automation_run_id: int,
    measure_elapsed: bool | None = None,
) -> dict[str, Any]:
    """Mark an automation run as completed.

    Args:
        automation_run_id: The automation run ID to complete.
        measure_elapsed: Auto-set execution time from creation to completion.
    """
    data: dict[str, Any] = {}
    if measure_elapsed is not None:
        data["measure_elapsed"] = measure_elapsed
    return await _request(
        "POST",
        f"/automation/runs/{automation_run_id}/complete",
        data=data if data else None,
    )


@mcp.tool()
async def testmo_create_automation_run_thread(
    automation_run_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new thread in an automation run for submitting test results.

    Threads represent parallel test execution lanes. After creating, use
    testmo_append_automation_run_thread to submit test results.

    Args:
        automation_run_id: The automation run ID.
        elapsed_observed: Observed execution time in microseconds.
        elapsed_computed: Computed execution time in microseconds.
        artifacts: External test artifacts for the thread.
        fields: Custom fields for the thread.
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    return await _request(
        "POST",
        f"/automation/runs/{automation_run_id}/threads",
        data=data if data else None,
    )


@mcp.tool()
async def testmo_append_automation_run_thread(
    thread_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    fields: list[dict[str, Any]] | None = None,
    tests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append test results, artifacts, or fields to an automation run thread.

    Each test in the 'tests' array: {key, name, folder, status, elapsed, file, line, assertions, artifacts, fields}.
    Status values: 'passed', 'failed', 'skipped', etc.

    Args:
        thread_id: The automation run thread ID.
        elapsed_observed: Partial observed time in microseconds to add.
        elapsed_computed: Partial computed time in microseconds to add.
        artifacts: External test artifacts to append.
        fields: Custom fields to append.
        tests: Test results to submit [{name, status, ...}].
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    if artifacts:
        data["artifacts"] = artifacts
    if fields:
        data["fields"] = fields
    if tests:
        data["tests"] = tests
    return await _request(
        "POST", f"/automation/runs/threads/{thread_id}/append", data=data
    )


@mcp.tool()
async def testmo_complete_automation_run_thread(
    thread_id: int,
    elapsed_observed: int | None = None,
    elapsed_computed: int | None = None,
) -> dict[str, Any]:
    """Mark an automation run thread as completed.

    Args:
        thread_id: The automation run thread ID to complete.
        elapsed_observed: Observed execution time in microseconds.
        elapsed_computed: Computed execution time in microseconds.
    """
    data: dict[str, Any] = {}
    if elapsed_observed is not None:
        data["elapsed_observed"] = elapsed_observed
    if elapsed_computed is not None:
        data["elapsed_computed"] = elapsed_computed
    return await _request(
        "POST",
        f"/automation/runs/threads/{thread_id}/complete",
        data=data if data else None,
    )
