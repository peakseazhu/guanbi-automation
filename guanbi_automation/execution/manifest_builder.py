from __future__ import annotations

from typing import Any

from guanbi_automation.domain.runtime_contract import PollingPolicy, RuntimeErrorInfo


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
    runtime_policy: PollingPolicy | None = None,
    final_error: RuntimeErrorInfo | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "extract_id": extract_id,
        "stage_name": stage_name,
        "events": events or [],
    }
    if runtime_policy is not None:
        manifest["runtime_policy"] = runtime_policy.model_dump(mode="json")
    if final_error is not None:
        manifest["final_error"] = final_error.model_dump(mode="json")
    return manifest
