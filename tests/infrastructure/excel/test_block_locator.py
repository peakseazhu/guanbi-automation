from guanbi_automation.infrastructure.excel.block_locator import (
    find_append_start_row,
    trim_trailing_empty_edges,
)


def test_append_start_row_uses_locator_columns_within_block_boundary():
    rows = [
        [None, "门店A", 100],
        [None, "门店B", 200],
        [None, None, None],
    ]

    start_row = find_append_start_row(
        rows=rows,
        anchor_row=2,
        locator_columns=[2, 3],
    )

    assert start_row == 4


def test_trim_trailing_empty_edges_keeps_internal_gaps():
    trimmed = trim_trailing_empty_edges(
        [
            ["区域", "值", None],
            ["华东", None, None],
            [None, None, None],
        ]
    )

    assert trimmed == [
        ["区域", "值"],
        ["华东", None],
    ]
