from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from guanbi_automation.application.publish_live_verification_service import (
    PublishLiveVerificationService,
)
from guanbi_automation.domain.live_verification import PublishLiveVerificationSpec


def test_service_archives_write_and_readback_evidence(tmp_path: Path):
    expected_rows = [["表头1", "表头2"], ["门店A", 100]]
    service = PublishLiveVerificationService(
        workbook_reader=lambda _spec: expected_rows,
        feishu_runtime=lambda _spec, normalized_rows: _successful_runtime(normalized_rows),
        evidence_root=tmp_path,
        clock=lambda: datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc),
    )

    result = service.run(_spec(tmp_path))

    assert result.status == "completed"
    assert result.comparison["matches"] is True
    assert result.evidence_dir == tmp_path / "publish" / "20260322T120000Z"
    assert (result.evidence_dir / "comparison.json").exists()
    assert (result.evidence_dir / "write-plan.json").exists()
    assert json.loads((result.evidence_dir / "comparison.json").read_text(encoding="utf-8"))[
        "matches"
    ] is True


def test_service_marks_failed_when_readback_mismatch(tmp_path: Path):
    expected_rows = [["表头1", "表头2"], ["门店A", 100]]
    service = PublishLiveVerificationService(
        workbook_reader=lambda _spec: expected_rows,
        feishu_runtime=lambda _spec, normalized_rows: _mismatch_runtime(normalized_rows),
        evidence_root=tmp_path,
        clock=lambda: datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc),
    )

    result = service.run(_spec(tmp_path))

    assert result.status == "failed"
    assert result.comparison["matches"] is False
    assert result.comparison["error_code"] == "publish_readback_mismatch"
    assert result.comparison["mismatch_count"] == 1


def _spec(tmp_path: Path) -> PublishLiveVerificationSpec:
    workbook_path = tmp_path / "执行管理字段更新版.xlsx"
    workbook_path.write_bytes(b"placeholder")
    return PublishLiveVerificationSpec(
        workbook_path=workbook_path,
        source_sheet_name="全国执行",
        source_start_row=1,
        source_start_col=1,
        header_mode="include",
        spreadsheet_token="spreadsheet-token",
        sheet_id="ySyhcD",
        target_start_row=1,
        target_start_col=1,
        write_mode="replace_sheet",
    )


def _successful_runtime(normalized_rows: list[list[object]]) -> dict[str, object]:
    return {
        "target_metadata": {"sheet_id": "ySyhcD", "title": "测试子表"},
        "write_plan": [
            {
                "range_string": "ySyhcD!A1:B2",
                "start_row": 1,
                "start_col": 1,
                "end_row": 2,
                "end_col": 2,
            }
        ],
        "write_result": {"responses": [{"updatedRange": "ySyhcD!A1:B2"}]},
        "readback": {
            "segments": [
                {
                    "range": "ySyhcD!A1:B2",
                    "values": normalized_rows,
                }
            ]
        },
        "actual_rows": normalized_rows,
    }


def _mismatch_runtime(normalized_rows: list[list[object]]) -> dict[str, object]:
    actual_rows = [list(row) for row in normalized_rows]
    actual_rows[1][1] = 101
    return {
        **_successful_runtime(normalized_rows),
        "readback": {
            "segments": [
                {
                    "range": "ySyhcD!A1:B2",
                    "values": actual_rows,
                }
            ]
        },
        "actual_rows": actual_rows,
    }
