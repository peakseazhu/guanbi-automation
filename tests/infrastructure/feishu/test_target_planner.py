import pytest

from guanbi_automation.domain.publish_contract import PublishDataset, PublishTargetSpec
from guanbi_automation.infrastructure.feishu.target_planner import (
    chunk_publish_rows,
    plan_range_segments,
    resolve_append_rows,
    resolve_replace_range,
    resolve_replace_sheet,
)


def test_replace_range_uses_dataset_shape_to_build_unique_target_range():
    dataset = PublishDataset(
        rows=[["x", 1], ["y", 2]],
        row_count=2,
        column_count=2,
        source_range="计算表1!A2:B3",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_id="sub-sheet-1",
        write_mode="replace_range",
        start_row=3,
        start_col=2,
    )

    resolved = resolve_replace_range(target=target, dataset=dataset, sheet_title="子表1")

    assert resolved.range_string == "子表1!B3:C4"


def test_replace_sheet_formats_multi_letter_a1_ranges():
    dataset = PublishDataset(
        rows=[[1, 2, 3], [4, 5, 6]],
        row_count=2,
        column_count=3,
        source_range="计算表2!A2:C3",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_name="子表2",
        write_mode="replace_sheet",
        start_row=5,
        start_col=27,
    )

    resolved = resolve_replace_sheet(target=target, dataset=dataset, sheet_title="子表2")

    assert resolved.range_string == "子表2!AA5:AC6"


def test_append_rows_uses_absolute_locator_columns_even_when_write_anchor_starts_later():
    dataset = PublishDataset(
        rows=[["门店B", 200]],
        row_count=1,
        column_count=2,
        source_range="计算表3!A2:B2",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_id="sub-sheet-3",
        write_mode="append_rows",
        start_row=2,
        start_col=2,
        append_locator_columns=[1],
    )

    resolved = resolve_append_rows(
        target=target,
        dataset=dataset,
        sheet_title="子表3",
        existing_rows=[
            ["批次-1", None],
            [None, None],
        ],
    )

    assert resolved.start_row == 3
    assert resolved.previous_last_row == 2
    assert resolved.range_string == "子表3!B3:C3"


def test_append_rows_starts_at_anchor_when_locator_columns_are_empty():
    dataset = PublishDataset(
        rows=[["门店D", 400], ["门店E", 500]],
        row_count=2,
        column_count=2,
        source_range="计算表4!A2:B3",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_name="子表4",
        write_mode="append_rows",
        start_row=4,
        start_col=2,
        append_locator_columns=[2, 3],
    )

    resolved = resolve_append_rows(
        target=target,
        dataset=dataset,
        sheet_title="子表4",
        existing_rows=[
            [None, None, None],
            [None, None, None],
        ],
    )

    assert resolved.start_row == 4
    assert resolved.previous_last_row is None
    assert resolved.range_string == "子表4!B4:C5"


def test_chunk_publish_rows_splits_dataset_by_row_limit():
    rows = [["a", 1], ["b", 2], ["c", 3]]

    chunks = chunk_publish_rows(rows=rows, chunk_row_limit=2)

    assert chunks == [
        [["a", 1], ["b", 2]],
        [["c", 3]],
    ]


def test_plan_range_segments_splits_wide_dataset_by_column_limit():
    segments = plan_range_segments(
        start_row=1,
        start_col=1,
        row_count=80,
        column_count=127,
        max_rows=5000,
        max_columns=100,
        sheet_id="ySyhcD",
    )

    assert [segment.range_string for segment in segments] == [
        "ySyhcD!A1:CV80",
        "ySyhcD!CW1:DW80",
    ]
    assert [(segment.start_col, segment.end_col) for segment in segments] == [
        (1, 100),
        (101, 127),
    ]


def test_plan_range_segments_splits_large_dataset_by_rows_and_columns():
    segments = plan_range_segments(
        start_row=5,
        start_col=2,
        row_count=520,
        column_count=127,
        max_rows=500,
        max_columns=100,
        sheet_id="ySyhcD",
    )

    assert [segment.range_string for segment in segments] == [
        "ySyhcD!B5:CW504",
        "ySyhcD!CX5:DX504",
        "ySyhcD!B505:CW524",
        "ySyhcD!CX505:DX524",
    ]
    assert [(segment.row_offset, segment.column_offset) for segment in segments] == [
        (0, 0),
        (0, 100),
        (500, 0),
        (500, 100),
    ]


def test_replace_range_rejects_explicit_bounds_smaller_than_dataset_shape():
    dataset = PublishDataset(
        rows=[["x", 1], ["y", 2]],
        row_count=2,
        column_count=2,
        source_range="计算表5!A2:B3",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_id="sub-sheet-5",
        write_mode="replace_range",
        start_row=3,
        start_col=2,
        end_row=3,
        end_col=2,
    )

    with pytest.raises(ValueError, match="dataset shape does not fit"):
        resolve_replace_range(target=target, dataset=dataset, sheet_title="子表5")


def test_replace_range_rejects_end_bounds_before_start():
    dataset = PublishDataset(
        rows=[["x"]],
        row_count=1,
        column_count=1,
        source_range="计算表6!A2:A2",
    )
    target = PublishTargetSpec(
        spreadsheet_token="sheet-token",
        sheet_id="sub-sheet-6",
        write_mode="replace_range",
        start_row=4,
        start_col=3,
        end_row=3,
        end_col=2,
    )

    with pytest.raises(ValueError, match="must not precede start"):
        resolve_replace_range(target=target, dataset=dataset, sheet_title="子表6")

