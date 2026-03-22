from pathlib import Path

from guanbi_automation.application.live_verification_spec import (
    load_publish_live_verification_spec,
)


def test_load_publish_live_verification_spec_from_yaml(tmp_path: Path):
    spec_path = tmp_path / "real_sample.local.yaml"
    spec_path.write_text(
        """
workbook_path: D:/get_bi_data__1/执行管理字段更新版.xlsx
source_sheet_name: 全国执行
source_start_row: 1
source_start_col: 1
header_mode: include
spreadsheet_token: sample-token
sheet_id: ySyhcD
target_start_row: 1
target_start_col: 1
write_mode: replace_sheet
""".strip(),
        encoding="utf-8",
    )

    spec = load_publish_live_verification_spec(spec_path)

    assert spec.sheet_id == "ySyhcD"
    assert spec.header_mode == "include"


def test_load_publish_live_verification_spec_resolves_workbook_path_to_path_object(
    tmp_path: Path,
):
    workbook_path = tmp_path / "workbook.xlsx"
    spec_path = tmp_path / "real_sample.local.yaml"
    spec_path.write_text(
        f"""
workbook_path: {workbook_path.as_posix()}
source_sheet_name: 全国执行
source_start_row: 1
source_start_col: 1
header_mode: include
spreadsheet_token: sample-token
sheet_id: ySyhcD
target_start_row: 1
target_start_col: 1
write_mode: replace_sheet
""".strip(),
        encoding="utf-8",
    )

    spec = load_publish_live_verification_spec(spec_path)

    assert spec.workbook_path == workbook_path
