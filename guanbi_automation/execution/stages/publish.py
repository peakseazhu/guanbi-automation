from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from guanbi_automation.domain.publish_contract import PublishDataset, PublishMappingSpec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.execution.manifest_builder import build_publish_manifest
from guanbi_automation.infrastructure.feishu.target_planner import ResolvedPublishTarget


@dataclass(frozen=True)
class PlannedPublishRun:
    batch_id: str
    job_id: str
    workbook_path: Path
    mappings: list[PublishMappingSpec]


@dataclass(frozen=True)
class PublishTargetContext:
    resolved_target: ResolvedPublishTarget
    append_rerun_error: RuntimeErrorInfo | None = None


@dataclass(frozen=True)
class PublishWriteResult:
    chunk_count: int
    successful_chunk_count: int
    written_row_count: int
    partial_write: bool
    segment_write_mode: str = "single_range"
    write_segments: list[dict[str, Any]] | None = None
    final_error: RuntimeErrorInfo | None = None
    events: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class PublishStageResult:
    status: str
    manifest: dict[str, Any]


class PublishStage:
    """Runs publish mappings and records mapping-level manifests."""

    def __init__(
        self,
        *,
        source_reader: Callable[[Path, Any], PublishDataset],
        target_loader: Callable[..., PublishTargetContext],
        target_writer: Callable[..., PublishWriteResult],
        empty_source_policy: str = "skip",
    ) -> None:
        self._source_reader = source_reader
        self._target_loader = target_loader
        self._target_writer = target_writer
        self._empty_source_policy = empty_source_policy

    def run(self, planned_run: PlannedPublishRun) -> PublishStageResult:
        mapping_manifests: list[dict[str, Any]] = []

        for mapping in planned_run.mappings:
            dataset = self._source_reader(planned_run.workbook_path, mapping.source)
            mapping_manifests.append(
                self._publish_mapping(
                    workbook_path=planned_run.workbook_path,
                    mapping=mapping,
                    dataset=dataset,
                )
            )

        final_status = _derive_publish_status(mapping_manifests)
        final_error = _resolve_final_error(mapping_manifests)
        manifest = build_publish_manifest(
            batch_id=planned_run.batch_id,
            job_id=planned_run.job_id,
            workbook_path=str(planned_run.workbook_path),
            mappings=mapping_manifests,
            final_status=final_status,
            final_error=final_error,
        )
        return PublishStageResult(status=final_status, manifest=manifest)

    def _publish_mapping(
        self,
        *,
        workbook_path: Path,
        mapping: PublishMappingSpec,
        dataset: PublishDataset,
    ) -> dict[str, Any]:
        empty_source = dataset.row_count == 0
        if empty_source and self._empty_source_policy == "skip":
            return _build_mapping_manifest(
                mapping=mapping,
                dataset=dataset,
                target_context=None,
                write_result=None,
                status="skipped",
                final_error=None,
                empty_source=True,
                empty_source_policy=self._empty_source_policy,
            )

        target_context = self._target_loader(
            workbook_path=workbook_path,
            mapping=mapping,
            dataset=dataset,
        )
        if target_context.append_rerun_error is not None:
            return _build_mapping_manifest(
                mapping=mapping,
                dataset=dataset,
                target_context=target_context,
                write_result=None,
                status="blocked",
                final_error=target_context.append_rerun_error,
                empty_source=empty_source,
                empty_source_policy=self._empty_source_policy if empty_source else None,
            )

        write_result = self._target_writer(
            workbook_path=workbook_path,
            mapping=mapping,
            dataset=dataset,
            target_context=target_context,
        )
        status = "failed" if write_result.final_error is not None else "completed"
        return _build_mapping_manifest(
            mapping=mapping,
            dataset=dataset,
            target_context=target_context,
            write_result=write_result,
            status=status,
            final_error=write_result.final_error,
            empty_source=empty_source,
            empty_source_policy=self._empty_source_policy if empty_source else None,
        )


def _build_mapping_manifest(
    *,
    mapping: PublishMappingSpec,
    dataset: PublishDataset,
    target_context: PublishTargetContext | None,
    write_result: PublishWriteResult | None,
    status: str,
    final_error: RuntimeErrorInfo | None,
    empty_source: bool,
    empty_source_policy: str | None,
) -> dict[str, Any]:
    resolved_target = target_context.resolved_target if target_context is not None else None
    write_segments = list(write_result.write_segments) if write_result and write_result.write_segments else []
    manifest: dict[str, Any] = {
        "mapping_id": mapping.mapping_id,
        "source": {
            "sheet_name": mapping.source.sheet_name,
            "read_mode": mapping.source.read_mode,
            "resolved_range": dataset.source_range,
            "header_mode": mapping.source.header_mode,
        },
        "target": {
            "spreadsheet_token": mapping.target.spreadsheet_token,
            "sheet_id": mapping.target.sheet_id,
            "sheet_name": mapping.target.sheet_name,
            "write_mode": mapping.target.write_mode,
            "resolved_target_range": (
                resolved_target.range_string if resolved_target is not None else None
            ),
        },
        "dataset_shape": {
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "cell_count": dataset.row_count * dataset.column_count,
        },
        "write_summary": {
            "chunk_count": write_result.chunk_count if write_result is not None else 0,
            "successful_chunk_count": (
                write_result.successful_chunk_count if write_result is not None else 0
            ),
            "written_row_count": write_result.written_row_count if write_result is not None else 0,
            "partial_write": write_result.partial_write if write_result is not None else False,
            "segment_count": len(write_segments),
            "segment_write_mode": (
                write_result.segment_write_mode if write_result is not None else None
            ),
        },
        "status": status,
        "final_error": final_error.model_dump(mode="json") if final_error is not None else None,
        "write_segments": write_segments,
        "events": list(write_result.events) if write_result and write_result.events else [],
        "empty_source": empty_source,
        "empty_source_policy": empty_source_policy,
    }

    if mapping.target.write_mode == "append_rows":
        manifest["append_anchor"] = {
            "start_row": mapping.target.start_row,
            "start_col": mapping.target.start_col,
        }
        manifest["append_locator_columns"] = list(mapping.target.append_locator_columns)
        manifest["previous_last_row"] = (
            resolved_target.previous_last_row if resolved_target is not None else None
        )
        manifest["new_last_row"] = (
            resolved_target.end_row if resolved_target is not None and status == "completed" else None
        )
        manifest["source_fingerprint"] = _fingerprint_rows(dataset.rows)

    return manifest


def _derive_publish_status(mappings: list[dict[str, Any]]) -> str:
    statuses = {mapping.get("status") for mapping in mappings}
    if "failed" in statuses:
        return "failed"
    if "blocked" in statuses:
        return "blocked"
    return "completed"


def _resolve_final_error(mappings: list[dict[str, Any]]) -> RuntimeErrorInfo | None:
    for status in ("failed", "blocked"):
        for mapping in mappings:
            if mapping.get("status") != status:
                continue
            final_error = mapping.get("final_error")
            if isinstance(final_error, dict):
                return RuntimeErrorInfo.model_validate(final_error)
    return None


def _fingerprint_rows(rows: list[list[object]]) -> str:
    serialized = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

