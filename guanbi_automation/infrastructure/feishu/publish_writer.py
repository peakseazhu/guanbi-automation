from __future__ import annotations

from typing import Any

from guanbi_automation.domain.publish_contract import PublishDataset, PublishMappingSpec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.stages.publish import PublishTargetContext, PublishWriteResult
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient, PublishClientError
from guanbi_automation.infrastructure.feishu.target_planner import (
    PlannedRangeSegment,
    plan_range_segments,
)


def write_publish_target(
    *,
    mapping: PublishMappingSpec,
    dataset: PublishDataset,
    target_context: PublishTargetContext,
    client: FeishuSheetsClient,
    tenant_access_token: str,
    chunk_row_limit: int,
    chunk_column_limit: int,
) -> PublishWriteResult:
    sheet_reference = (
        target_context.resolved_target.sheet_id or target_context.resolved_target.sheet_title
    )
    segments = plan_range_segments(
        start_row=target_context.resolved_target.start_row,
        start_col=target_context.resolved_target.start_col,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        max_rows=chunk_row_limit,
        max_columns=chunk_column_limit,
        sheet_id=sheet_reference,
    )
    write_segments = [_serialize_segment(segment) for segment in segments]
    chunk_count = 1 if segments else 0
    segment_write_mode = "single_range" if len(segments) <= 1 else "batch_ranges"
    operation = "write_values" if len(segments) <= 1 else "write_values_batch"
    successful_chunk_count = 0

    try:
        if not segments:
            return PublishWriteResult(
                chunk_count=0,
                successful_chunk_count=0,
                written_row_count=0,
                partial_write=False,
                segment_write_mode="single_range",
                write_segments=[],
                events=[
                    _build_event(
                        event="publish_target_write_completed",
                        operation="write_values",
                        segment_count=0,
                        segment_write_mode="single_range",
                    )
                ],
            )

        if len(segments) == 1:
            segment = segments[0]
            client.write_values(
                spreadsheet_token=mapping.target.spreadsheet_token,
                range_string=segment.range_string,
                rows=_slice_segment_rows(dataset.rows, segment),
                tenant_access_token=tenant_access_token,
            )
        else:
            client.write_values_batch(
                spreadsheet_token=mapping.target.spreadsheet_token,
                value_ranges=[
                    {
                        "range": segment.range_string,
                        "values": _slice_segment_rows(dataset.rows, segment),
                    }
                    for segment in segments
                ],
                tenant_access_token=tenant_access_token,
            )
        successful_chunk_count = chunk_count
    except PublishClientError as exc:
        return PublishWriteResult(
            chunk_count=chunk_count,
            successful_chunk_count=successful_chunk_count,
            written_row_count=dataset.row_count if successful_chunk_count else 0,
            partial_write=successful_chunk_count > 0,
            segment_write_mode=segment_write_mode,
            write_segments=write_segments,
            final_error=exc.error,
            events=[
                _build_event(
                    event="publish_target_write_failed",
                    operation=operation,
                    segment_count=len(segments),
                    segment_write_mode=segment_write_mode,
                    error_code=exc.error.code.value,
                )
            ],
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        final_error = RuntimeErrorInfo(
            code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
            message=str(exc),
            retryable=False,
        )
        return PublishWriteResult(
            chunk_count=chunk_count,
            successful_chunk_count=successful_chunk_count,
            written_row_count=dataset.row_count if successful_chunk_count else 0,
            partial_write=successful_chunk_count > 0,
            segment_write_mode=segment_write_mode,
            write_segments=write_segments,
            final_error=final_error,
            events=[
                _build_event(
                    event="publish_target_write_failed",
                    operation=operation,
                    segment_count=len(segments),
                    segment_write_mode=segment_write_mode,
                    error_code=final_error.code.value,
                )
            ],
        )

    return PublishWriteResult(
        chunk_count=chunk_count,
        successful_chunk_count=successful_chunk_count,
        written_row_count=dataset.row_count,
        partial_write=False,
        segment_write_mode=segment_write_mode,
        write_segments=write_segments,
        events=[
            _build_event(
                event="publish_target_write_completed",
                operation=operation,
                segment_count=len(segments),
                segment_write_mode=segment_write_mode,
            )
        ],
    )


def _slice_segment_rows(
    rows: list[list[object]],
    segment: PlannedRangeSegment,
) -> list[list[object]]:
    sliced_rows: list[list[object]] = []
    for row_index in range(segment.row_offset, segment.row_offset + segment.row_count):
        row = rows[row_index] if row_index < len(rows) else []
        sliced_rows.append(
            [
                row[column_index] if column_index < len(row) else ""
                for column_index in range(
                    segment.column_offset,
                    segment.column_offset + segment.column_count,
                )
            ]
        )
    return sliced_rows


def _serialize_segment(segment: PlannedRangeSegment) -> dict[str, Any]:
    return {
        "range_string": segment.range_string,
        "row_count": segment.row_count,
        "column_count": segment.column_count,
        "row_offset": segment.row_offset,
        "column_offset": segment.column_offset,
    }


def _build_event(
    *,
    event: str,
    operation: str,
    segment_count: int,
    segment_write_mode: str,
    error_code: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "event": event,
        "operation": operation,
        "segment_count": segment_count,
        "segment_write_mode": segment_write_mode,
    }
    if error_code is not None:
        payload["error_code"] = error_code
    return payload
