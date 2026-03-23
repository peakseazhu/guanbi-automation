from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from guanbi_automation.application.publish_runtime_service import run_publish_runtime
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


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

    first = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
    )
    second = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
    )

    assert first.stage_name == "publish"
    assert first.status == "preflight_failed"
    assert first.batch_id == "publish-cli"
    assert first.job_id == _expected_job_id(workbook_path, spec_path)
    assert first.manifest is None
    assert first.final_error is not None
    assert first.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR
    assert "not implemented yet" in first.final_error.message
    assert second.batch_id == first.batch_id
    assert second.job_id == first.job_id


def test_run_publish_runtime_normalizes_blank_ids_to_default_values(tmp_path: Path):
    workbook_path = _write_workbook(tmp_path)
    spec_path = _write_publish_spec(tmp_path, write_mode="replace_range")

    result = run_publish_runtime(
        workbook_path=workbook_path,
        spec_path=spec_path,
        tenant_access_token="tenant-token",
        batch_id="   ",
        job_id="",
    )

    assert result.stage_name == "publish"
    assert result.status == "preflight_failed"
    assert result.batch_id == "publish-cli"
    assert result.job_id == _expected_job_id(workbook_path, spec_path)
    assert result.manifest is None
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.CONFIGURATION_ERROR
    assert "not implemented yet" in result.final_error.message


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
) -> Path:
    append_locator_lines = (
        "      append_locator_columns: [1]\n" if write_mode == "append_rows" else ""
    )
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
        "      sheet_id: ySyhcD\n"
        f"      write_mode: {write_mode}\n"
        "      start_row: 3\n"
        "      start_col: 2\n"
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
