from __future__ import annotations

from dataclasses import dataclass

from guanbi_automation.domain.publish_contract import PublishDataset, PublishTargetSpec
from guanbi_automation.infrastructure.excel.block_locator import find_append_start_row


@dataclass(frozen=True)
class ResolvedPublishTarget:
    sheet_id: str
    sheet_title: str
    range_string: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    previous_last_row: int | None = None


@dataclass(frozen=True)
class PlannedRangeSegment:
    sheet_id: str
    range_string: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    row_count: int
    column_count: int
    row_offset: int
    column_offset: int


def resolve_replace_sheet(
    *,
    target: PublishTargetSpec,
    dataset: PublishDataset,
    sheet_title: str,
) -> ResolvedPublishTarget:
    return _resolve_bounded_target(
        target=target,
        dataset=dataset,
        sheet_title=sheet_title,
        start_row=target.start_row,
        previous_last_row=None,
    )


def resolve_replace_range(
    *,
    target: PublishTargetSpec,
    dataset: PublishDataset,
    sheet_title: str,
) -> ResolvedPublishTarget:
    return _resolve_bounded_target(
        target=target,
        dataset=dataset,
        sheet_title=sheet_title,
        start_row=target.start_row,
        previous_last_row=None,
    )


def resolve_append_rows(
    *,
    target: PublishTargetSpec,
    dataset: PublishDataset,
    sheet_title: str,
    existing_rows: list[list[object]],
) -> ResolvedPublishTarget:
    start_row = find_append_start_row(
        rows=existing_rows,
        anchor_row=target.start_row,
        locator_columns=target.append_locator_columns,
    )
    previous_last_row = start_row - 1 if start_row > target.start_row else None
    return _resolve_bounded_target(
        target=target,
        dataset=dataset,
        sheet_title=sheet_title,
        start_row=start_row,
        previous_last_row=previous_last_row,
    )


def chunk_publish_rows(
    *,
    rows: list[list[object]],
    chunk_row_limit: int,
) -> list[list[list[object]]]:
    if chunk_row_limit < 1:
        raise ValueError("chunk_row_limit must be positive")
    return [
        rows[index:index + chunk_row_limit]
        for index in range(0, len(rows), chunk_row_limit)
    ]


def plan_range_segments(
    *,
    start_row: int,
    start_col: int,
    row_count: int,
    column_count: int,
    max_rows: int,
    max_columns: int,
    sheet_id: str,
) -> list[PlannedRangeSegment]:
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    if max_columns < 1:
        raise ValueError("max_columns must be positive")
    if row_count < 1 or column_count < 1:
        return []

    segments: list[PlannedRangeSegment] = []
    for row_offset in range(0, row_count, max_rows):
        segment_row_count = min(max_rows, row_count - row_offset)
        segment_start_row = start_row + row_offset
        segment_end_row = segment_start_row + segment_row_count - 1

        for column_offset in range(0, column_count, max_columns):
            segment_column_count = min(max_columns, column_count - column_offset)
            segment_start_col = start_col + column_offset
            segment_end_col = segment_start_col + segment_column_count - 1
            segments.append(
                PlannedRangeSegment(
                    sheet_id=sheet_id,
                    range_string=_build_a1_range(
                        sheet_id,
                        segment_start_row,
                        segment_start_col,
                        segment_end_row,
                        segment_end_col,
                    ),
                    start_row=segment_start_row,
                    start_col=segment_start_col,
                    end_row=segment_end_row,
                    end_col=segment_end_col,
                    row_count=segment_row_count,
                    column_count=segment_column_count,
                    row_offset=row_offset,
                    column_offset=column_offset,
                )
            )

    return segments


def _resolve_bounded_target(
    *,
    target: PublishTargetSpec,
    dataset: PublishDataset,
    sheet_title: str,
    start_row: int,
    previous_last_row: int | None,
) -> ResolvedPublishTarget:
    end_row = _resolve_end_index(
        start_index=start_row,
        explicit_end=target.end_row,
        inferred_size=dataset.row_count,
    )
    end_col = _resolve_end_index(
        start_index=target.start_col,
        explicit_end=target.end_col,
        inferred_size=dataset.column_count,
    )
    return ResolvedPublishTarget(
        sheet_id=target.sheet_id or "",
        sheet_title=sheet_title,
        range_string=_build_a1_range(
            sheet_title,
            start_row,
            target.start_col,
            end_row,
            end_col,
        ),
        start_row=start_row,
        start_col=target.start_col,
        end_row=end_row,
        end_col=end_col,
        previous_last_row=previous_last_row,
    )


def _resolve_end_index(
    *,
    start_index: int,
    explicit_end: int | None,
    inferred_size: int,
) -> int:
    if explicit_end is not None:
        if explicit_end < start_index:
            raise ValueError("publish target end index must not precede start index")
        if inferred_size > 0 and (explicit_end - start_index + 1) < inferred_size:
            raise ValueError("publish target dataset shape does not fit explicit bounds")
        return explicit_end
    if inferred_size < 1:
        return start_index
    return start_index + inferred_size - 1


def _build_a1_range(
    sheet_title: str,
    start_row: int,
    start_col: int,
    end_row: int,
    end_col: int,
) -> str:
    return (
        f"{sheet_title}!"
        f"{_column_label(start_col)}{start_row}:"
        f"{_column_label(end_col)}{end_row}"
    )


def _column_label(column_number: int) -> str:
    label = ""
    current = column_number

    while current > 0:
        current, remainder = divmod(current - 1, 26)
        label = chr(65 + remainder) + label

    return label

