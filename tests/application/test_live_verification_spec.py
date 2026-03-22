from pathlib import Path

from guanbi_automation.application.live_verification_spec import (
    load_publish_live_verification_spec,
)
from guanbi_automation.live_verification.publish_real_sample import (
    resolve_default_spec_path,
    resolve_env_path,
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


def test_default_spec_path_points_to_local_publish_live_verification_file():
    path = resolve_default_spec_path(Path("D:/get_bi_data__1"))

    assert path.as_posix().endswith(
        "config/live_verification/publish/real_sample.local.yaml"
    )


def test_resolve_env_path_falls_back_to_shared_repo_root_for_worktree(tmp_path: Path):
    project_root = tmp_path / ".worktrees" / "publish-stage-task1"
    project_root.mkdir(parents=True)
    shared_env_path = tmp_path / ".env"
    shared_env_path.write_text('FEISHU_APP_ID="app-id"\n', encoding="utf-8")

    resolved = resolve_env_path(project_root)

    assert resolved == shared_env_path
