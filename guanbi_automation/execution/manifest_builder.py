from __future__ import annotations

from typing import Any

from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    PollingPolicy,
    RuntimeErrorInfo,
)


def build_batch_manifest(
    *,
    batch_id: str,
    runtime_policy: PollingPolicy | None = None,
    final_error: RuntimeErrorInfo | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "batch_id": batch_id,
        "events": events or [],
    }
    if runtime_policy is not None:
        manifest["runtime_policy"] = runtime_policy.model_dump(mode="json")
    if final_error is not None:
        manifest["final_error"] = final_error.model_dump(mode="json")
    return manifest


def build_extract_manifest(
    *,
    extract_id: str,
    stage_name: str,
    runtime_policy: ExtractRuntimePolicy | None = None,
    template_runtime_profile: str | None = None,
    effective_runtime_profile: str | None = None,
    submit_attempts: int = 0,
    submit_elapsed_seconds: float = 0.0,
    submit_final_error: RuntimeErrorInfo | None = None,
    poll_attempts: int = 0,
    poll_total_wait_seconds: float = 0.0,
    poll_elapsed_seconds: float = 0.0,
    poll_final_error: RuntimeErrorInfo | None = None,
    download_attempts: int = 0,
    download_elapsed_seconds: float = 0.0,
    download_final_error: RuntimeErrorInfo | None = None,
    extract_total_elapsed_seconds: float = 0.0,
    deadline_exhausted: bool = False,
    final_error: RuntimeErrorInfo | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "extract_id": extract_id,
        "stage_name": stage_name,
        "events": events or [],
        "template_runtime_profile": template_runtime_profile,
        "effective_runtime_profile": effective_runtime_profile,
        "submit_attempts": submit_attempts,
        "submit_elapsed_seconds": submit_elapsed_seconds,
        "submit_final_error": (
            submit_final_error.model_dump(mode="json")
            if submit_final_error is not None
            else None
        ),
        "poll_attempts": poll_attempts,
        "poll_total_wait_seconds": poll_total_wait_seconds,
        "poll_elapsed_seconds": poll_elapsed_seconds,
        "poll_final_error": (
            poll_final_error.model_dump(mode="json") if poll_final_error is not None else None
        ),
        "download_attempts": download_attempts,
        "download_elapsed_seconds": download_elapsed_seconds,
        "download_final_error": (
            download_final_error.model_dump(mode="json")
            if download_final_error is not None
            else None
        ),
        "extract_total_elapsed_seconds": extract_total_elapsed_seconds,
        "deadline_exhausted": deadline_exhausted,
    }
    if runtime_policy is not None:
        manifest["runtime_policy"] = runtime_policy.model_dump(mode="json")
    if final_error is not None:
        manifest["final_error"] = final_error.model_dump(mode="json")
    return manifest


def build_workbook_manifest(
    *,
    batch_id: str,
    job_id: str,
    stage_name: str,
    template_path: str,
    result_path: str,
    blocks: list[dict[str, Any]],
    completed: bool,
    calculation_completed: bool | None = None,
    final_error: RuntimeErrorInfo | None = None,
) -> dict[str, Any]:
    manifest = {
        "batch_id": batch_id,
        "job_id": job_id,
        "stage_name": stage_name,
        "template_path": template_path,
        "result_path": result_path,
        "blocks": blocks,
        "completed": completed,
    }
    if calculation_completed is not None:
        manifest["calculation_completed"] = calculation_completed
    if final_error is not None:
        manifest["final_error"] = final_error.model_dump(mode="json")
    return manifest


def build_publish_manifest(
    *,
    batch_id: str,
    job_id: str,
    workbook_path: str,
    mappings: list[dict[str, Any]],
    final_status: str,
    final_error: RuntimeErrorInfo | None = None,
) -> dict[str, Any]:
    status_counts = _count_mapping_statuses(mappings)
    manifest: dict[str, Any] = {
        "batch_id": batch_id,
        "job_id": job_id,
        "stage_name": "publish",
        "result_workbook_path": workbook_path,
        "mapping_count": len(mappings),
        "completed_mapping_count": status_counts["completed"],
        "failed_mapping_count": status_counts["failed"],
        "blocked_mapping_count": status_counts["blocked"],
        "skipped_mapping_count": status_counts["skipped"],
        "final_status": final_status,
        "mappings": mappings,
    }
    if final_error is not None:
        manifest["final_error"] = final_error.model_dump(mode="json")
    return manifest


def _count_mapping_statuses(mappings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "completed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
    }
    for mapping in mappings:
        status = mapping.get("status")
        if status in counts:
            counts[status] += 1
    return counts
