from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from guanbi_automation.application.publish_runtime_spec import load_publish_runtime_spec
from guanbi_automation.bootstrap.settings import PublishSettings
from guanbi_automation.domain.publish_contract import PublishDataset, PublishMappingSpec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.manifest_builder import build_publish_manifest
from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.execution.stages.publish import (
    PlannedPublishRun,
    PublishStage,
    PublishTargetContext,
)
from guanbi_automation.infrastructure.excel.publish_source_reader import read_publish_source
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient, PublishClientError
from guanbi_automation.infrastructure.feishu.publish_writer import write_publish_target
from guanbi_automation.infrastructure.feishu.target_planner import (
    resolve_replace_range,
    resolve_replace_sheet,
)


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
    default_job_id = _default_job_id(
        workbook_path=workbook_path,
        spec_path=spec_path,
    )
    resolved_batch_id = _normalize_identifier(
        batch_id,
        default_value="publish-cli",
    )
    resolved_job_id = _normalize_identifier(
        job_id,
        default_value=default_job_id,
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

    client = client_factory() if client_factory is not None else FeishuSheetsClient()
    settings = PublishSettings()
    target_loader = _build_target_loader(
        client=client,
        tenant_access_token=tenant_access_token,
    )
    resolved_source_reader = source_reader or read_publish_source
    resolved_target_writer = target_writer or _build_target_writer(
        client=client,
        tenant_access_token=tenant_access_token,
        settings=settings,
    )
    publish_stage = PublishStage(
        source_reader=resolved_source_reader,
        target_loader=target_loader,
        target_writer=resolved_target_writer,
        empty_source_policy=settings.empty_source_policy,
    )
    pipeline = PipelineEngine(
        extract_stage=_NullExtractStage(),
        publish_stage=publish_stage,
    )
    try:
        stage_result = pipeline.run_publish(
            PlannedPublishRun(
                batch_id=resolved_batch_id,
                job_id=resolved_job_id,
                workbook_path=workbook_path,
                mappings=spec.mappings,
            )
        )
    except Exception as exc:  # pragma: no cover - stage should absorb mapping failures
        final_error = RuntimeErrorInfo(
            code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
            message=str(exc) or exc.__class__.__name__,
            retryable=False,
            details={"exception_type": exc.__class__.__name__},
        )
        return PublishRuntimeResult(
            status="failed",
            batch_id=resolved_batch_id,
            job_id=resolved_job_id,
            manifest=build_publish_manifest(
                batch_id=resolved_batch_id,
                job_id=resolved_job_id,
                workbook_path=str(workbook_path),
                mappings=[],
                final_status="failed",
                final_error=final_error,
            ),
            final_error=final_error,
        )

    return PublishRuntimeResult(
        status=stage_result.status,
        batch_id=resolved_batch_id,
        job_id=resolved_job_id,
        manifest=stage_result.manifest,
        final_error=_extract_final_error(stage_result.manifest),
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


def _normalize_identifier(value: str | None, *, default_value: str) -> str:
    if value is None or not value.strip():
        return default_value
    return value


def _build_target_loader(
    *,
    client: Any,
    tenant_access_token: str,
) -> Callable[..., PublishTargetContext]:
    def _load_target(
        *,
        workbook_path: Path,
        mapping: PublishMappingSpec,
        dataset: PublishDataset,
    ) -> PublishTargetContext:
        _ = workbook_path
        sheets = client.query_sheets(
            mapping.target.spreadsheet_token,
            tenant_access_token,
        )
        resolved_sheet_id, resolved_sheet_title = _resolve_sheet_metadata(
            mapping=mapping,
            sheets=sheets,
        )
        if mapping.target.write_mode == "replace_sheet":
            resolved_target = resolve_replace_sheet(
                target=mapping.target,
                dataset=dataset,
                sheet_title=resolved_sheet_title,
            )
        elif mapping.target.write_mode == "replace_range":
            resolved_target = resolve_replace_range(
                target=mapping.target,
                dataset=dataset,
                sheet_title=resolved_sheet_title,
            )
        else:  # pragma: no cover - append_rows stays blocked at preflight for this task
            raise ValueError(f"Unsupported publish write mode: {mapping.target.write_mode}")

        if resolved_sheet_id is not None and resolved_sheet_id != resolved_target.sheet_id:
            resolved_target = replace(resolved_target, sheet_id=resolved_sheet_id)

        return PublishTargetContext(resolved_target=resolved_target)

    return _load_target


def _build_target_writer(
    *,
    client: Any,
    tenant_access_token: str,
    settings: PublishSettings,
) -> Callable[..., Any]:
    def _write_target(
        *,
        workbook_path: Path,
        mapping: PublishMappingSpec,
        dataset: PublishDataset,
        target_context: PublishTargetContext,
    ) -> Any:
        _ = workbook_path
        return write_publish_target(
            mapping=mapping,
            dataset=dataset,
            target_context=target_context,
            client=client,
            tenant_access_token=tenant_access_token,
            chunk_row_limit=settings.chunk_row_limit,
            chunk_column_limit=settings.chunk_column_limit,
        )

    return _write_target


def _resolve_sheet_metadata(
    *,
    mapping: PublishMappingSpec,
    sheets: list[dict[str, object]],
) -> tuple[str | None, str]:
    requested_sheet_id = _normalize_optional_identifier(mapping.target.sheet_id)
    if requested_sheet_id is not None:
        for sheet in sheets:
            if _normalize_optional_identifier(_sheet_field(sheet, "sheet_id")) == requested_sheet_id:
                return requested_sheet_id, _resolve_sheet_title(sheet)
        raise _missing_target_error(
            mapping=mapping,
            field_name="sheet_id",
            requested_value=requested_sheet_id,
        )

    requested_sheet_name = _normalize_optional_identifier(mapping.target.sheet_name)
    if requested_sheet_name is not None:
        for sheet in sheets:
            if _normalize_optional_identifier(_sheet_field(sheet, "title")) == requested_sheet_name:
                return _normalize_optional_identifier(_sheet_field(sheet, "sheet_id")), _resolve_sheet_title(sheet)
        raise _missing_target_error(
            mapping=mapping,
            field_name="sheet_name",
            requested_value=requested_sheet_name,
        )

    raise _missing_target_error(
        mapping=mapping,
        field_name="sheet_name",
        requested_value="<missing>",
    )


def _sheet_field(sheet: dict[str, object], field_name: str) -> str | None:
    value = sheet.get(field_name)
    return value if isinstance(value, str) else None


def _resolve_sheet_title(sheet: dict[str, object]) -> str:
    sheet_title = _normalize_optional_identifier(_sheet_field(sheet, "title"))
    if sheet_title is None:
        raise PublishClientError(
            "query_sheets",
            RuntimeErrorInfo(
                code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
                message="Feishu sheet metadata is missing title",
                retryable=False,
            ),
        )
    return sheet_title


def _normalize_optional_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _missing_target_error(
    *,
    mapping: PublishMappingSpec,
    field_name: str,
    requested_value: str,
) -> PublishClientError:
    return PublishClientError(
        "query_sheets",
        RuntimeErrorInfo(
            code=RuntimeErrorCode.PUBLISH_TARGET_MISSING,
            message=f"Publish target {field_name} '{requested_value}' was not found",
            retryable=False,
            details={
                "spreadsheet_token": mapping.target.spreadsheet_token,
                field_name: requested_value,
            },
        ),
    )


def _extract_final_error(manifest: dict[str, object]) -> RuntimeErrorInfo | None:
    final_error = manifest.get("final_error")
    if isinstance(final_error, dict):
        return RuntimeErrorInfo.model_validate(final_error)
    return None


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


class _NullExtractStage:
    def run(self, planned_run: Any) -> Any:
        return planned_run
