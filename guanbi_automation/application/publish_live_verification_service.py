from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict

from guanbi_automation.domain.live_verification import (
    PublishCellValue,
    PublishLiveVerificationSpec,
    canonicalize_publish_cell,
)
from guanbi_automation.domain.publish_contract import PublishSourceSpec
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.excel.publish_source_reader import read_publish_source
from guanbi_automation.infrastructure.feishu.client import (
    FeishuSheetsClient,
    PublishClientError,
)
from guanbi_automation.infrastructure.feishu.target_planner import (
    PlannedRangeSegment,
    plan_range_segments,
)

WorkbookReader = Callable[[PublishLiveVerificationSpec], list[list[PublishCellValue]]]
FeishuRuntime = Callable[
    [PublishLiveVerificationSpec, list[list[PublishCellValue]]],
    dict[str, object],
]
Clock = Callable[[], datetime]


class PublishLiveVerificationResult(BaseModel):
    """Stable result envelope for one live publish verification run."""

    model_config = ConfigDict(frozen=True)

    status: Literal["completed", "failed"]
    evidence_dir: Path
    comparison: dict[str, object]


class PublishLiveVerificationService:
    """Runs a real publish sample, then archives write/readback evidence."""

    def __init__(
        self,
        *,
        workbook_reader: WorkbookReader | None = None,
        feishu_runtime: FeishuRuntime | None = None,
        evidence_root: Path | str = Path("runs/live_verification"),
        clock: Clock | None = None,
        app_id: str | None = None,
        app_secret: str | None = None,
        client_factory: Callable[[], FeishuSheetsClient] | None = None,
    ) -> None:
        self._evidence_root = Path(evidence_root)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._app_id = app_id
        self._app_secret = app_secret
        self._client_factory = client_factory or FeishuSheetsClient
        self._workbook_reader = workbook_reader or self._read_workbook_rows
        self._feishu_runtime = feishu_runtime or self._run_feishu_runtime

    def run(self, spec: PublishLiveVerificationSpec) -> PublishLiveVerificationResult:
        evidence_dir = self._resolve_evidence_dir()
        evidence_dir.mkdir(parents=True, exist_ok=False)

        source_rows: list[list[PublishCellValue]] = []
        source_metadata = _build_source_metadata(spec=spec, rows=source_rows)
        target_metadata: dict[str, object] = {}
        write_plan: object = []
        write_result: object = {}
        readback: object = {}
        comparison: dict[str, object]

        try:
            source_rows = self._workbook_reader(spec)
            source_metadata = _build_source_metadata(spec=spec, rows=source_rows)

            runtime_payload = self._feishu_runtime(spec, source_rows)
            target_metadata = _coerce_mapping(runtime_payload.get("target_metadata"))
            write_plan = runtime_payload.get("write_plan", [])
            write_result = runtime_payload.get("write_result", {})
            readback = runtime_payload.get("readback", {})
            actual_rows = _coerce_matrix(runtime_payload.get("actual_rows"))

            comparison = _compare_matrices(expected_rows=source_rows, actual_rows=actual_rows)
            status: Literal["completed", "failed"] = (
                "completed" if comparison["matches"] else "failed"
            )
        except PublishClientError as exc:
            comparison = _build_failure_comparison(
                error=exc.error,
                expected_rows=source_rows,
                actual_rows=[],
            )
            status = "failed"
        except Exception as exc:  # pragma: no cover - defensive fallback
            error_code = (
                RuntimeErrorCode.PUBLISH_SOURCE_READ_ERROR
                if not source_rows
                else RuntimeErrorCode.PUBLISH_WRITE_ERROR
            )
            comparison = _build_failure_comparison(
                error=RuntimeErrorInfo(
                    code=error_code,
                    message=str(exc),
                    retryable=False,
                ),
                expected_rows=source_rows,
                actual_rows=[],
            )
            status = "failed"

        _write_json(evidence_dir / "request.json", spec.model_dump(mode="json"))
        _write_json(evidence_dir / "source-metadata.json", source_metadata)
        _write_json(evidence_dir / "target-metadata.json", target_metadata)
        _write_json(evidence_dir / "write-plan.json", write_plan)
        _write_json(evidence_dir / "write-result.json", write_result)
        _write_json(evidence_dir / "readback.json", readback)
        _write_json(evidence_dir / "comparison.json", comparison)

        return PublishLiveVerificationResult(
            status=status,
            evidence_dir=evidence_dir,
            comparison=comparison,
        )

    def _read_workbook_rows(
        self,
        spec: PublishLiveVerificationSpec,
    ) -> list[list[PublishCellValue]]:
        source = PublishSourceSpec(
            source_id="publish-live-verification",
            sheet_name=spec.source_sheet_name,
            read_mode="sheet",
            start_row=spec.source_start_row,
            start_col=spec.source_start_col,
            header_mode=spec.header_mode,
        )
        dataset = read_publish_source(spec.workbook_path, source)
        return [
            [canonicalize_publish_cell(cell) for cell in row]
            for row in dataset.rows
        ]

    def _run_feishu_runtime(
        self,
        spec: PublishLiveVerificationSpec,
        normalized_rows: list[list[PublishCellValue]],
    ) -> dict[str, object]:
        if not self._app_id or not self._app_secret:
            raise ValueError("publish live verification requires app_id and app_secret")

        client = self._client_factory()
        token_payload = client.fetch_tenant_access_token(self._app_id, self._app_secret)
        tenant_access_token = token_payload.get("tenant_access_token")
        if not isinstance(tenant_access_token, str) or not tenant_access_token.strip():
            raise PublishClientError(
                "fetch_tenant_access_token",
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.PUBLISH_AUTH_ERROR,
                    message="Feishu response is missing tenant_access_token",
                    retryable=False,
                ),
            )

        sheets = client.query_sheets(spec.spreadsheet_token, tenant_access_token)
        target_sheet = _resolve_target_sheet_metadata(
            sheets=sheets,
            spreadsheet_token=spec.spreadsheet_token,
            sheet_id=spec.sheet_id,
        )

        row_count = len(normalized_rows)
        column_count = max((len(row) for row in normalized_rows), default=0)
        segments = plan_range_segments(
            start_row=spec.target_start_row,
            start_col=spec.target_start_col,
            row_count=row_count,
            column_count=column_count,
            max_rows=5000,
            max_columns=100,
            sheet_id=spec.sheet_id,
        )

        value_ranges = [
            {
                "range": segment.range_string,
                "values": _slice_segment_rows(normalized_rows, segment),
            }
            for segment in segments
        ]

        write_payload: dict[str, object] = {"data": {"responses": []}}
        if value_ranges:
            write_payload = client.write_values_batch(
                spreadsheet_token=spec.spreadsheet_token,
                value_ranges=value_ranges,
                tenant_access_token=tenant_access_token,
            )

        actual_rows = _blank_matrix(row_count=row_count, column_count=column_count)
        readback_segments: list[dict[str, object]] = []
        for segment in segments:
            payload = client.read_values(
                spreadsheet_token=spec.spreadsheet_token,
                range_string=segment.range_string,
                tenant_access_token=tenant_access_token,
            )
            segment_values = _extract_readback_values(payload)
            _overlay_segment(actual_rows=actual_rows, segment=segment, segment_values=segment_values)
            readback_segments.append(
                {
                    "range": segment.range_string,
                    "values": segment_values,
                }
            )

        return {
            "target_metadata": {
                **target_sheet,
                "token_expire_seconds": token_payload.get("expire"),
            },
            "write_plan": [_json_ready(segment) for segment in segments],
            "write_result": write_payload,
            "readback": {"segments": readback_segments},
            "actual_rows": actual_rows,
        }

    def _resolve_evidence_dir(self) -> Path:
        timestamp = self._clock().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self._evidence_root / "publish" / timestamp


def _compare_matrices(
    *,
    expected_rows: list[list[object]],
    actual_rows: list[list[object]],
) -> dict[str, object]:
    expected_shape = _matrix_shape(expected_rows)
    actual_shape = _matrix_shape(actual_rows)
    compared_row_count = max(expected_shape["row_count"], actual_shape["row_count"])
    compared_column_count = max(
        expected_shape["column_count"],
        actual_shape["column_count"],
    )

    expected_matrix = _normalize_matrix(
        expected_rows,
        row_count=compared_row_count,
        column_count=compared_column_count,
    )
    actual_matrix = _normalize_matrix(
        actual_rows,
        row_count=compared_row_count,
        column_count=compared_column_count,
    )

    mismatch_count = 0
    first_mismatch: dict[str, object] | None = None
    for row_index in range(compared_row_count):
        for column_index in range(compared_column_count):
            expected_value = expected_matrix[row_index][column_index]
            actual_value = actual_matrix[row_index][column_index]
            if expected_value == actual_value:
                continue
            mismatch_count += 1
            if first_mismatch is None:
                first_mismatch = {
                    "row": row_index + 1,
                    "column": column_index + 1,
                    "expected": expected_value,
                    "actual": actual_value,
                }

    matches = mismatch_count == 0
    comparison: dict[str, object] = {
        "matches": matches,
        "expected_shape": expected_shape,
        "actual_shape": actual_shape,
        "compared_row_count": compared_row_count,
        "compared_column_count": compared_column_count,
        "mismatch_count": mismatch_count,
        "first_mismatch": first_mismatch,
        "expected_preview": expected_matrix[:3],
        "actual_preview": actual_matrix[:3],
    }
    if not matches:
        comparison["error_code"] = RuntimeErrorCode.PUBLISH_READBACK_MISMATCH.value
    return comparison


def _build_failure_comparison(
    *,
    error: RuntimeErrorInfo,
    expected_rows: list[list[object]],
    actual_rows: list[list[object]],
) -> dict[str, object]:
    comparison = _compare_matrices(expected_rows=expected_rows, actual_rows=actual_rows)
    comparison["matches"] = False
    comparison["error_code"] = error.code.value
    comparison["error_message"] = error.message
    comparison["retryable"] = error.retryable
    comparison["error_details"] = error.details
    return comparison


def _build_source_metadata(
    *,
    spec: PublishLiveVerificationSpec,
    rows: list[list[object]],
) -> dict[str, object]:
    shape = _matrix_shape(rows)
    return {
        "workbook_path": str(spec.workbook_path),
        "source_sheet_name": spec.source_sheet_name,
        "source_start_row": spec.source_start_row,
        "source_start_col": spec.source_start_col,
        "header_mode": spec.header_mode,
        "row_count": shape["row_count"],
        "column_count": shape["column_count"],
        "preview": _normalize_matrix(
            rows,
            row_count=min(shape["row_count"], 3),
            column_count=shape["column_count"],
        ),
    }


def _resolve_target_sheet_metadata(
    *,
    sheets: list[dict[str, object]],
    spreadsheet_token: str,
    sheet_id: str,
) -> dict[str, object]:
    for sheet in sheets:
        if sheet.get("sheet_id") == sheet_id:
            return {
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
                "title": sheet.get("title"),
                "hidden": sheet.get("hidden"),
            }
    raise PublishClientError(
        "query_sheets",
        RuntimeErrorInfo(
            code=RuntimeErrorCode.PUBLISH_TARGET_MISSING,
            message=f"Feishu sheet_id not found: {sheet_id}",
            retryable=False,
            details={"sheet_id": sheet_id},
        ),
    )


def _slice_segment_rows(
    rows: list[list[PublishCellValue]],
    segment: PlannedRangeSegment,
) -> list[list[PublishCellValue]]:
    sliced_rows: list[list[PublishCellValue]] = []
    for row_index in range(segment.row_offset, segment.row_offset + segment.row_count):
        row = rows[row_index] if row_index < len(rows) else []
        segment_values: list[PublishCellValue] = []
        for column_index in range(
            segment.column_offset,
            segment.column_offset + segment.column_count,
        ):
            if column_index < len(row):
                segment_values.append(canonicalize_publish_cell(row[column_index]))
            else:
                segment_values.append("")
        sliced_rows.append(segment_values)
    return sliced_rows


def _extract_readback_values(payload: dict[str, object]) -> list[list[PublishCellValue]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    value_range = data.get("valueRange")
    if not isinstance(value_range, dict):
        return []
    return _coerce_matrix(value_range.get("values"))


def _overlay_segment(
    *,
    actual_rows: list[list[PublishCellValue]],
    segment: PlannedRangeSegment,
    segment_values: list[list[PublishCellValue]],
) -> None:
    for row_index in range(segment.row_count):
        destination_row = segment.row_offset + row_index
        if destination_row >= len(actual_rows):
            break
        current_row = segment_values[row_index] if row_index < len(segment_values) else []
        for column_index in range(segment.column_count):
            destination_col = segment.column_offset + column_index
            if destination_col >= len(actual_rows[destination_row]):
                break
            if column_index < len(current_row):
                actual_rows[destination_row][destination_col] = canonicalize_publish_cell(
                    current_row[column_index]
                )


def _normalize_matrix(
    rows: list[list[object]],
    *,
    row_count: int,
    column_count: int,
) -> list[list[PublishCellValue]]:
    normalized_rows: list[list[PublishCellValue]] = []
    for row_index in range(row_count):
        source_row = rows[row_index] if row_index < len(rows) else []
        normalized_row: list[PublishCellValue] = []
        for column_index in range(column_count):
            if column_index < len(source_row):
                normalized_row.append(canonicalize_publish_cell(source_row[column_index]))
            else:
                normalized_row.append("")
        normalized_rows.append(normalized_row)
    return normalized_rows


def _blank_matrix(*, row_count: int, column_count: int) -> list[list[PublishCellValue]]:
    return [["" for _ in range(column_count)] for _ in range(row_count)]


def _matrix_shape(rows: list[list[object]]) -> dict[str, int]:
    return {
        "row_count": len(rows),
        "column_count": max((len(row) for row in rows), default=0),
    }


def _coerce_matrix(value: object) -> list[list[PublishCellValue]]:
    if not isinstance(value, list):
        return []
    matrix: list[list[PublishCellValue]] = []
    for row in value:
        if not isinstance(row, list):
            matrix.append([])
            continue
        matrix.append([canonicalize_publish_cell(cell) for cell in row])
    return matrix


def _coerce_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(_json_ready(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _json_ready(payload: object) -> object:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Path):
        return str(payload)
    if is_dataclass(payload):
        return {key: _json_ready(value) for key, value in asdict(payload).items()}
    if isinstance(payload, dict):
        return {str(key): _json_ready(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_json_ready(item) for item in payload]
    if isinstance(payload, tuple):
        return [_json_ready(item) for item in payload]
    return payload
