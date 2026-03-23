from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from guanbi_automation.application.publish_runtime_spec import load_publish_runtime_spec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


class PublishRuntimeResult(BaseModel):
    """Stable publish runtime envelope returned to callers and CLI adapters."""

    model_config = ConfigDict(frozen=True)

    stage_name: Literal["publish"] = "publish"
    status: Literal["preflight_failed", "completed", "blocked", "failed"]
    batch_id: str
    job_id: str
    manifest: dict[str, object] | None = None
    final_error: RuntimeErrorInfo | None = None


def run_publish_runtime(
    *,
    workbook_path: Path | None,
    spec_path: Path | None,
    tenant_access_token: str | None,
    batch_id: str | None = None,
    job_id: str | None = None,
    client_factory: Callable[..., Any] | None = None,
    source_reader: Callable[..., Any] | None = None,
    target_writer: Callable[..., Any] | None = None,
) -> PublishRuntimeResult:
    resolved_batch_id = batch_id if batch_id is not None else "publish-cli"
    resolved_job_id = (
        job_id
        if job_id is not None
        else _default_job_id(
            workbook_path=workbook_path,
            spec_path=spec_path,
        )
    )

    if workbook_path is None:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="workbook_path is required",
            details={"field": "workbook_path"},
        )
    if spec_path is None:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="spec_path is required",
            details={"field": "spec_path"},
        )
    if tenant_access_token is None or not tenant_access_token.strip():
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="tenant_access_token is required",
            details={"field": "tenant_access_token"},
        )

    try:
        spec = load_publish_runtime_spec(spec_path)
    except (OSError, TypeError, ValidationError, ValueError) as exc:
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message=str(exc),
            details={"spec_path": str(spec_path)},
        )

    if any(mapping.target.write_mode == "append_rows" for mapping in spec.mappings):
        return _preflight_failure(
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            message="append_rows is not wired into the first mainline publish consumer",
            details={"unsupported_write_mode": "append_rows"},
        )

    _ = client_factory, source_reader, target_writer

    return PublishRuntimeResult(
        status="completed",
        batch_id=resolved_batch_id,
        job_id=resolved_job_id,
    )


def _default_job_id(*, workbook_path: Path | None, spec_path: Path | None) -> str:
    workbook_key = _resolved_path_key(
        workbook_path,
        missing_placeholder="<missing-workbook>",
    )
    spec_key = _resolved_path_key(
        spec_path,
        missing_placeholder="<missing-spec>",
    )
    digest = hashlib.sha256(f"{workbook_key}|{spec_key}".encode("utf-8")).hexdigest()[:12]
    return f"publish-{digest}"


def _resolved_path_key(path: Path | None, *, missing_placeholder: str) -> str:
    if path is None:
        return missing_placeholder
    return str(Path(path).resolve())


def _preflight_failure(
    *,
    batch_id: str,
    job_id: str,
    message: str,
    details: dict[str, object],
) -> PublishRuntimeResult:
    return PublishRuntimeResult(
        status="preflight_failed",
        batch_id=batch_id,
        job_id=job_id,
        final_error=RuntimeErrorInfo(
            code=RuntimeErrorCode.CONFIGURATION_ERROR,
            message=message,
            details=details,
        ),
    )
