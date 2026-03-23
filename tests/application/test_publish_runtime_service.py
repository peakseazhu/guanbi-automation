from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
from openpyxl import Workbook

import guanbi_automation.application.publish_runtime_service as publish_runtime_service
from guanbi_automation.bootstrap.settings import PublishSettings
from guanbi_automation.domain.publish_contract import PublishDataset
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.application.publish_runtime_service import run_publish_runtime
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.stages.publish import PublishWriteResult
from guanbi_automation.infrastructure.feishu.client import PublishClientError


def test_run_publish_runtime_rejects_append_rows_before_stage_entry(
    tmp_path: Path,
):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="append_rows")

    def fail_if_called(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("publish runtime should stop at preflight")

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=fail_if_called,
        source_reader=fail_if_called,
        target_writer=fail_if_called,
    )

    assert result.stage_name == "publish"
    assert result.status == "preflight_failed"
    assert result.batch_id == "publish-cli"
    assert result.job_id == _expected_job_id(workbook_path, spec_path)
    assert result.manifest is None
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR
    assert "append_rows" in result.final_error.message
    assert result.final_error.details == {"unsupported_write_mode": "append_rows"}


def test_run_publish_runtime_uses_deterministic_default_ids(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")
    client = _FakeSheetsClient(sheets=[{"sheet_id": "ySyhcD", "title": "子表1"}])

    first = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: client,
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100], ["store-b", 200]]),
        target_writer=lambda *_args, dataset, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=dataset.row_count,
        ),
    )
    second = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: client,
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100], ["store-b", 200]]),
        target_writer=lambda *_args, dataset, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=dataset.row_count,
        ),
    )

    assert first.stage_name == "publish"
    assert first.status == "completed"
    assert first.batch_id == "publish-cli"
    assert first.job_id == _expected_job_id(workbook_path, spec_path)
    assert first.manifest is not None
    assert first.manifest["mappings"][0]["target"]["resolved_target_range"] == "子表1!B3:C4"
    assert first.final_error is None
    assert second.batch_id == first.batch_id
    assert second.job_id == first.job_id


def test_run_publish_runtime_normalizes_blank_ids_to_default_values(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(
        tmp_path,
        write_mode="replace_range",
        target_sheet_name="Fallback By Name",
    )
    resolved_ranges: list[str] = []
    client = _FakeSheetsClient(
        sheets=[
            {"sheet_id": "fallback-sheet", "title": "Fallback By Name"},
            {"sheet_id": "ySyhcD", "title": "Resolved By Id"},
        ]
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        batch_id="   ",
        job_id="",
        client_factory=lambda: client,
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
        target_writer=lambda *_args, target_context, dataset, **_kwargs: (
            resolved_ranges.append(target_context.resolved_target.range_string)
            or _write_result(
                chunk_count=1,
                written_row_count=dataset.row_count,
            )
        ),
    )

    assert result.stage_name == "publish"
    assert result.status == "completed"
    assert result.batch_id == "publish-cli"
    assert result.job_id == _expected_job_id(workbook_path, spec_path)
    assert result.manifest is not None
    assert result.manifest["mappings"][0]["target"]["sheet_id"] == "ySyhcD"
    assert result.manifest["mappings"][0]["target"]["sheet_name"] == "Resolved By Id"
    assert resolved_ranges == ["Resolved By Id!B3:C3"]
    assert result.final_error is None


def test_run_publish_runtime_normalizes_source_reader_failures_to_failed_result(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        source_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("source workbook is unreadable")
        ),
        client_factory=lambda: _FakeSheetsClient(sheets=[{"sheet_id": "ySyhcD", "title": "子表1"}]),
    )

    assert result.status == "failed"
    assert result.manifest is not None
    assert result.manifest["failed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["status"] == "failed"
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.PUBLISH_SOURCE_READ_ERROR
    assert result.final_error.message == "source workbook is unreadable"


def test_run_publish_runtime_normalizes_target_planner_failures_to_failed_result(tmp_path: Path):
    workbook_path = _write_publish_workbook(tmp_path)
    spec_path = _write_publish_spec(
        tmp_path,
        write_mode="replace_range",
        target_end_row=3,
        target_end_col=2,
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: _FakeSheetsClient(sheets=[{"sheet_id": "ySyhcD", "title": "子表1"}]),
    )

    assert result.status == "failed"
    assert result.manifest is not None
    assert result.manifest["failed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["status"] == "failed"
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.PUBLISH_RANGE_INVALID
    assert "dataset shape does not fit explicit bounds" in result.final_error.message


def test_run_publish_runtime_normalizes_query_transport_failures_to_failed_result(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")

    class _TransportFailingClient:
        def query_sheets(self, *_args, **_kwargs):
            raise httpx.ConnectError("query_sheets transport failed")

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: _TransportFailingClient(),
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
    )

    assert result.status == "failed"
    assert result.manifest is not None
    assert result.manifest["failed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["status"] == "failed"
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.PUBLISH_WRITE_ERROR
    assert result.final_error.message == "query_sheets transport failed"


def test_run_publish_runtime_propagates_failed_status_from_writer_errors(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")
    client_error = PublishClientError(
        "write_values",
        RuntimeErrorInfo(
            code=RuntimeErrorCode.PUBLISH_RANGE_INVALID,
            message="invalid publish range",
            retryable=False,
        ),
    )
    client = _FakeSheetsClient(
        sheets=[{"sheet_id": "ySyhcD", "title": "子表1"}],
        write_error=client_error,
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: client,
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
    )

    assert result.status == "failed"
    assert result.manifest is not None
    assert result.manifest["failed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["status"] == "failed"
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.PUBLISH_RANGE_INVALID
    assert result.final_error.message == "invalid publish range"


def test_run_publish_runtime_uses_default_target_writer_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workbook_path = _write_publish_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")
    client = _FakeSheetsClient(sheets=[{"sheet_id": "ySyhcD", "title": "子表1"}])
    captured_calls: list[dict[str, object]] = []
    original_write_publish_target = publish_runtime_service.write_publish_target

    def spy_write_publish_target(**kwargs: object) -> PublishWriteResult:
        captured_calls.append(kwargs)
        assert "workbook_path" not in kwargs
        return original_write_publish_target(**kwargs)

    monkeypatch.setattr(
        publish_runtime_service,
        "write_publish_target",
        spy_write_publish_target,
    )

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        client_factory=lambda: client,
    )

    assert result.status == "completed"
    assert result.manifest is not None
    assert result.manifest["completed_mapping_count"] == 1
    assert captured_calls
    assert captured_calls[0]["client"] is client
    assert captured_calls[0]["tenant_access_token"] == "tenant-token"
    assert captured_calls[0]["chunk_row_limit"] == PublishSettings().chunk_row_limit
    assert captured_calls[0]["chunk_column_limit"] == PublishSettings().chunk_column_limit
    assert client.write_calls == [
        {
            "spreadsheet_token": "sheet-token",
            "range_string": "ySyhcD!B3:C4",
            "rows": [["store-a", 100], ["store-b", 200]],
            "tenant_access_token": "tenant-token",
        }
    ]


@pytest.mark.parametrize(
    ("workbook_path", "spec_path", "tenant_access_token", "field"),
    [
        (None, "valid", "tenant-token", "workbook_path"),
        ("valid", None, "tenant-token", "spec_path"),
        ("valid", "valid", None, "tenant_access_token"),
        ("valid", "valid", "   ", "tenant_access_token"),
    ],
)
def test_run_publish_runtime_normalizes_missing_inputs(
    tmp_path: Path,
    workbook_path: str | None,
    spec_path: str | None,
    tenant_access_token: str | None,
    field: str,
):
    resolved_workbook_path = (
        _write_workbook(tmp_path, "input.xlsx") if workbook_path == "valid" else None
    )
    resolved_spec_path = (
        _write_publish_spec(tmp_path, file_name="publish.yaml")
        if spec_path == "valid"
        else None
    )

    result = run_publish_runtime(
        workbook_path=resolved_workbook_path,
        spec_path=resolved_spec_path,
        tenant_access_token=tenant_access_token,
    )

    assert result.stage_name == "publish"
    assert result.status == "preflight_failed"
    assert result.batch_id == "publish-cli"
    assert result.job_id == _expected_job_id(resolved_workbook_path, resolved_spec_path)
    assert result.manifest is None
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR
    assert result.final_error.details == {"field": field}


@pytest.mark.parametrize(
    "payload",
    [
        "mappings:\n  - mapping_id: broken: [\n",
        "{}\n",
    ],
)
def test_run_publish_runtime_normalizes_spec_load_failures(
    tmp_path: Path,
    payload: str,
):
    workbook_path = _write_workbook(tmp_path)
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(payload, encoding="utf-8")

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
    )

    assert result.stage_name == "publish"
    assert result.status == "preflight_failed"
    assert result.batch_id == "publish-cli"
    assert result.job_id == _expected_job_id(workbook_path, spec_path)
    assert result.manifest is None
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR
    assert result.final_error.message
    assert result.final_error.details == {"spec_path": str(spec_path)}


def _write_workbook(tmp_path: Path, file_name: str = "result.xlsx") -> Path:
    workbook_path = tmp_path / file_name
    workbook_path.write_bytes(b"placeholder")
    return workbook_path


def _write_publish_spec(
    tmp_path: Path,
    *,
    write_mode: str = "replace_range",
    file_name: str = "publish.yaml",
    target_sheet_id: str | None = "ySyhcD",
    target_sheet_name: str | None = None,
    target_end_row: int | None = None,
    target_end_col: int | None = None,
) -> Path:
    append_locator_lines = (
        "      append_locator_columns: [1]\n" if write_mode == "append_rows" else ""
    )
    target_sheet_id_line = (
        f"      sheet_id: {target_sheet_id}\n" if target_sheet_id is not None else ""
    )
    target_sheet_name_line = (
        f"      sheet_name: {target_sheet_name}\n" if target_sheet_name is not None else ""
    )
    target_end_row_line = f"      end_row: {target_end_row}\n" if target_end_row is not None else ""
    target_end_col_line = f"      end_col: {target_end_col}\n" if target_end_col is not None else ""
    spec_path = tmp_path / file_name
    spec_path.write_text(
        "mappings:\n"
        "  - mapping_id: publish-sales\n"
        "    source:\n"
        "      source_id: sales-sheet\n"
        "      sheet_name: 计算表1\n"
        "      read_mode: sheet\n"
        "      start_row: 2\n"
        "      start_col: 1\n"
        "      header_mode: exclude\n"
        "    target:\n"
        "      spreadsheet_token: sheet-token\n"
        f"{target_sheet_id_line}"
        f"{target_sheet_name_line}"
        f"      write_mode: {write_mode}\n"
        "      start_row: 3\n"
        "      start_col: 2\n"
        f"{target_end_row_line}"
        f"{target_end_col_line}"
        f"{append_locator_lines}",
        encoding="utf-8",
    )
    return spec_path


def _expected_job_id(workbook_path: Path | None, spec_path: Path | None) -> str:
    workbook_key = (
        str(workbook_path.resolve())
        if workbook_path is not None
        else "<missing-workbook>"
    )
    spec_key = str(spec_path.resolve()) if spec_path is not None else "<missing-spec>"
    digest = hashlib.sha256(f"{workbook_key}|{spec_key}".encode("utf-8")).hexdigest()[:12]
    return f"publish-{digest}"


def _dataset(*, rows: list[list[object]]) -> PublishDataset:
    return PublishDataset(
        rows=rows,
        row_count=len(rows),
        column_count=max((len(row) for row in rows), default=0),
        source_range="计算表1!A3:B4",
    )


def _write_result(
    *,
    chunk_count: int,
    written_row_count: int,
    final_error: RuntimeErrorInfo | None = None,
) -> PublishWriteResult:
    return PublishWriteResult(
        chunk_count=chunk_count,
        successful_chunk_count=chunk_count if final_error is None else 0,
        written_row_count=written_row_count if final_error is None else 0,
        partial_write=False,
        final_error=final_error,
    )


def _write_publish_workbook(tmp_path: Path, file_name: str = "result.xlsx") -> Path:
    workbook_path = tmp_path / file_name
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "计算表1"
    sheet["A2"] = "门店"
    sheet["B2"] = "销售额"
    sheet["A3"] = "store-a"
    sheet["B3"] = 100
    sheet["A4"] = "store-b"
    sheet["B4"] = 200
    workbook.save(workbook_path)
    workbook.close()
    return workbook_path


class _FakeSheetsClient:
    def __init__(
        self,
        *,
        sheets: list[dict[str, object]],
        write_error: PublishClientError | None = None,
    ) -> None:
        self._sheets = list(sheets)
        self._write_error = write_error
        self.query_calls: list[dict[str, object]] = []
        self.write_calls: list[dict[str, object]] = []
        self.write_batch_calls: list[dict[str, object]] = []

    def query_sheets(
        self,
        spreadsheet_token: str,
        tenant_access_token: str,
    ) -> list[dict[str, object]]:
        self.query_calls.append(
            {
                "spreadsheet_token": spreadsheet_token,
                "tenant_access_token": tenant_access_token,
            }
        )
        return list(self._sheets)

    def write_values(
        self,
        *,
        spreadsheet_token: str,
        range_string: str,
        rows: list[list[object]],
        tenant_access_token: str,
    ) -> dict[str, object]:
        self.write_calls.append(
            {
                "spreadsheet_token": spreadsheet_token,
                "range_string": range_string,
                "rows": rows,
                "tenant_access_token": tenant_access_token,
            }
        )
        if self._write_error is not None:
            raise self._write_error
        return {"code": 0, "data": {"updatedRange": range_string}}

    def write_values_batch(
        self,
        *,
        spreadsheet_token: str,
        value_ranges: list[dict[str, object]],
        tenant_access_token: str,
    ) -> dict[str, object]:
        self.write_batch_calls.append(
            {
                "spreadsheet_token": spreadsheet_token,
                "value_ranges": value_ranges,
                "tenant_access_token": tenant_access_token,
            }
        )
        if self._write_error is not None:
            raise self._write_error
        return {"code": 0, "data": {"responses": value_ranges}}
