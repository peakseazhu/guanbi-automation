from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from guanbi_automation.domain.publish_contract import PublishDataset, PublishSourceSpec
from guanbi_automation.infrastructure.excel.block_locator import trim_trailing_empty_edges


def read_publish_source(workbook_path: Path, source: PublishSourceSpec) -> PublishDataset:
    workbook = load_workbook(workbook_path, data_only=True)
    sheet = workbook[source.sheet_name]
    rows = _read_bounded_rows(sheet=sheet, source=source)

    if source.header_mode == "exclude" and rows:
        rows = rows[1:]

    trimmed_rows = trim_trailing_empty_edges(rows)
    row_count = len(trimmed_rows)
    column_count = max((len(row) for row in trimmed_rows), default=0)
    return PublishDataset(
        rows=trimmed_rows,
        row_count=row_count,
        column_count=column_count,
        source_range=_format_source_range(source=source, rows=trimmed_rows),
    )


def _read_bounded_rows(*, sheet: object, source: PublishSourceSpec) -> list[list[object]]:
    max_row = source.end_row or getattr(sheet, "max_row")
    max_col = source.end_col or getattr(sheet, "max_column")

    rows: list[list[object]] = []
    for row_index in range(source.start_row, max_row + 1):
        row_values: list[object] = []
        for col_index in range(source.start_col, max_col + 1):
            row_values.append(sheet.cell(row=row_index, column=col_index).value)
        rows.append(row_values)

    return trim_trailing_empty_edges(rows)


def _format_source_range(*, source: PublishSourceSpec, rows: list[list[object]]) -> str:
    if not rows:
        return (
            f"{source.sheet_name}!"
            f"{_column_label(source.start_col)}{source.start_row}:"
            f"{_column_label(source.start_col)}{source.start_row}"
        )

    end_row = source.start_row + len(rows) - 1
    end_col = source.start_col + max((len(row) for row in rows), default=1) - 1
    return (
        f"{source.sheet_name}!"
        f"{_column_label(source.start_col)}{source.start_row}:"
        f"{_column_label(end_col)}{end_row}"
    )


def _column_label(column_number: int) -> str:
    label = ""
    current = column_number

    while current > 0:
        current, remainder = divmod(current - 1, 26)
        label = chr(65 + remainder) + label

    return label
