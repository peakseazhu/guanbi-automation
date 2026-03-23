from pathlib import Path

import pytest
from pydantic import ValidationError

from guanbi_automation.application.publish_runtime_spec import (
    PublishRuntimeSpec,
    load_publish_runtime_spec,
)
from guanbi_automation.domain.publish_contract import PublishMappingSpec


def test_load_publish_runtime_spec_reuses_publish_mapping_contract(tmp_path: Path):
    spec_path = tmp_path / "publish.yaml"
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
        "      write_mode: replace_range\n"
        "      start_row: 3\n"
        "      start_col: 2\n",
        encoding="utf-8",
    )

    spec = load_publish_runtime_spec(spec_path)

    assert isinstance(spec, PublishRuntimeSpec)
    assert isinstance(spec.mappings[0], PublishMappingSpec)
    assert spec.mappings[0].target.write_mode == "replace_range"


def test_load_publish_runtime_spec_rejects_non_mapping_payload(tmp_path: Path):
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text("- bad\n", encoding="utf-8")

    with pytest.raises(ValueError, match="publish runtime spec must be a mapping"):
        load_publish_runtime_spec(spec_path)


@pytest.mark.parametrize(
    "payload",
    [
        "{}\n",
        "mappings: []\n",
    ],
)
def test_load_publish_runtime_spec_rejects_missing_or_empty_mappings(
    tmp_path: Path,
    payload: str,
):
    spec_path = tmp_path / "publish.yaml"
    spec_path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_publish_runtime_spec(spec_path)
