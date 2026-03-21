import pytest

from guanbi_automation.bootstrap.settings import PublishSettings
from guanbi_automation.domain.publish_contract import PublishSourceSpec, PublishTargetSpec


def test_publish_source_defaults_to_excluding_headers():
    source = PublishSourceSpec(
        source_id="calc-1",
        sheet_name="计算表1",
        read_mode="sheet",
        start_row=2,
        start_col=1,
    )

    assert source.header_mode == "exclude"


def test_append_rows_target_requires_locator_columns():
    with pytest.raises(ValueError):
        PublishTargetSpec(
            spreadsheet_token="sheet-token",
            sheet_id="sub-sheet-1",
            write_mode="append_rows",
            start_row=2,
            start_col=1,
        )


def test_publish_target_requires_sheet_identifier():
    with pytest.raises(ValueError):
        PublishTargetSpec(
            spreadsheet_token="sheet-token",
            write_mode="replace_sheet",
            start_row=2,
            start_col=1,
        )


@pytest.mark.parametrize(
    ("sheet_id", "sheet_name"),
    [
        ("", None),
        ("   ", None),
        (None, ""),
        (None, "   "),
        ("", "   "),
    ],
)
def test_publish_target_rejects_blank_sheet_identifiers(
    sheet_id: str | None,
    sheet_name: str | None,
):
    with pytest.raises(ValueError):
        PublishTargetSpec(
            spreadsheet_token="sheet-token",
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            write_mode="replace_sheet",
            start_row=2,
            start_col=1,
        )


def test_publish_settings_have_safe_defaults():
    settings = PublishSettings()

    assert settings.chunk_row_limit > 0
    assert settings.empty_source_policy == "skip"
