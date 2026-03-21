from __future__ import annotations


def _is_empty(value: object) -> bool:
    return value is None or value == ""


def trim_trailing_empty_edges(rows: list[list[object]]) -> list[list[object]]:
    trimmed_rows = [list(row) for row in rows]

    while trimmed_rows and all(_is_empty(cell) for cell in trimmed_rows[-1]):
        trimmed_rows.pop()

    if not trimmed_rows:
        return []

    max_width = max(len(row) for row in trimmed_rows)
    last_non_empty_col = 0
    for row in trimmed_rows:
        for index, cell in enumerate(row, start=1):
            if not _is_empty(cell):
                last_non_empty_col = max(last_non_empty_col, index)

    if last_non_empty_col == 0:
        return []

    return [row[:last_non_empty_col] for row in trimmed_rows]


def find_append_start_row(
    *,
    rows: list[list[object]],
    anchor_row: int,
    locator_columns: list[int],
) -> int:
    trimmed_rows = trim_trailing_empty_edges(rows)
    last_data_offset = 0

    for row_index, row in enumerate(trimmed_rows, start=1):
        if any(
            column <= len(row) and not _is_empty(row[column - 1])
            for column in locator_columns
        ):
            last_data_offset = row_index

    if last_data_offset == 0:
        return anchor_row
    return anchor_row + last_data_offset
