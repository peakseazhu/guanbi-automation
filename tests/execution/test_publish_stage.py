from pathlib import Path

from guanbi_automation.domain.publish_contract import (
    PublishDataset,
    PublishMappingSpec,
    PublishSourceSpec,
    PublishTargetSpec,
)
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.execution.stages.publish import (
    PlannedPublishRun,
    PublishStage,
    PublishTargetContext,
    PublishWriteResult,
)
from guanbi_automation.infrastructure.feishu.target_planner import ResolvedPublishTarget


def test_publish_stage_records_mapping_level_results(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["x", 1], ["y", 2]]),
        target_loader=lambda *_args, **_kwargs: _target_context(),
        target_writer=lambda *_args, **_kwargs: _write_result(chunk_count=1, written_row_count=2),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.status == "completed"
    assert result.manifest["completed_mapping_count"] == 1
    assert result.manifest["mappings"][0]["write_summary"]["written_row_count"] == 2


def test_publish_stage_manifest_records_segment_summary(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(
            rows=[[f"col-{index}" for index in range(127)]]
        ),
        target_loader=lambda *_args, **_kwargs: _target_context(),
        target_writer=lambda *_args, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=1,
            segment_write_mode="batch_ranges",
            write_segments=[
                {
                    "range_string": "子表1!B3:CW3",
                    "row_count": 1,
                    "column_count": 100,
                    "row_offset": 0,
                    "column_offset": 0,
                },
                {
                    "range_string": "子表1!CX3:EU3",
                    "row_count": 1,
                    "column_count": 27,
                    "row_offset": 0,
                    "column_offset": 100,
                },
            ],
        ),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.manifest["mappings"][0]["write_summary"]["segment_count"] == 2
    assert result.manifest["mappings"][0]["write_summary"]["segment_write_mode"] == "batch_ranges"
    assert result.manifest["mappings"][0]["write_segments"][1]["column_offset"] == 100


def test_publish_stage_skips_empty_source_when_policy_is_skip(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    target_loader_calls: list[str] = []
    target_writer_calls: list[str] = []

    def target_loader(*_args, **_kwargs) -> PublishTargetContext:
        target_loader_calls.append("called")
        return _target_context()

    def target_writer(*_args, **_kwargs) -> PublishWriteResult:
        target_writer_calls.append("called")
        return _write_result(chunk_count=0, written_row_count=0)

    stage = PublishStage(
        empty_source_policy="skip",
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[]),
        target_loader=target_loader,
        target_writer=target_writer,
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec()],
        )
    )

    assert result.status == "completed"
    assert result.manifest["skipped_mapping_count"] == 1
    assert result.manifest["mappings"][0]["status"] == "skipped"
    assert result.manifest["mappings"][0]["empty_source"] is True
    assert result.manifest["mappings"][0]["empty_source_policy"] == "skip"
    assert target_loader_calls == []
    assert target_writer_calls == []


def test_publish_stage_blocks_append_rerun_before_write(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    target_writer_calls: list[str] = []

    def target_writer(*_args, **_kwargs) -> PublishWriteResult:
        target_writer_calls.append("called")
        return _write_result(chunk_count=1, written_row_count=1)

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
        target_loader=lambda *_args, **_kwargs: _target_context(
            previous_last_row=12,
            append_rerun_error=RuntimeErrorInfo(
                code=RuntimeErrorCode.PUBLISH_APPEND_RERUN_BLOCKED,
                message="Append rerun blocked",
                retryable=False,
            ),
        ),
        target_writer=target_writer,
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[_mapping_spec(write_mode="append_rows")],
        )
    )

    assert result.status == "blocked"
    assert result.manifest["blocked_mapping_count"] == 1
    assert result.manifest["mappings"][0]["final_error"]["code"] == RuntimeErrorCode.PUBLISH_APPEND_RERUN_BLOCKED
    assert result.manifest["mappings"][0]["previous_last_row"] == 12
    assert result.manifest["mappings"][0]["source_fingerprint"]
    assert target_writer_calls == []


def test_pipeline_engine_delegates_to_publish_stage(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[]),
        target_loader=lambda *_args, **_kwargs: _target_context(),
        target_writer=lambda *_args, **_kwargs: _write_result(chunk_count=0, written_row_count=0),
    )
    engine = PipelineEngine(
        extract_stage=_extract_stage_stub(),
        publish_stage=stage,
    )

    result = engine.run_publish(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[],
        )
    )

    assert result.manifest["stage_name"] == "publish"


def _mapping_spec(
    *,
    mapping_id: str = "mapping-001",
    write_mode: str = "replace_range",
) -> PublishMappingSpec:
    append_locator_columns = [2] if write_mode == "append_rows" else []
    return PublishMappingSpec(
        mapping_id=mapping_id,
        source=PublishSourceSpec(
            source_id="calc-1",
            sheet_name="计算表1",
            read_mode="sheet",
            start_row=2,
            start_col=1,
        ),
        target=PublishTargetSpec(
            spreadsheet_token="sheet-token",
            sheet_id="sub-sheet-1",
            write_mode=write_mode,
            start_row=3,
            start_col=2,
            append_locator_columns=append_locator_columns,
        ),
    )


def _dataset(*, rows: list[list[object]]) -> PublishDataset:
    return PublishDataset(
        rows=rows,
        row_count=len(rows),
        column_count=max((len(row) for row in rows), default=0),
        source_range="计算表1!A2:B3",
    )


def _target_context(
    *,
    previous_last_row: int | None = None,
    append_rerun_error: RuntimeErrorInfo | None = None,
) -> PublishTargetContext:
    return PublishTargetContext(
        resolved_target=ResolvedPublishTarget(
            sheet_id="sub-sheet-1",
            sheet_title="子表1",
            range_string="子表1!B3:C4",
            start_row=3,
            start_col=2,
            end_row=4,
            end_col=3,
            previous_last_row=previous_last_row,
        ),
        append_rerun_error=append_rerun_error,
    )


def _write_result(
    *,
    chunk_count: int,
    written_row_count: int,
    successful_chunk_count: int | None = None,
    partial_write: bool = False,
    segment_write_mode: str = "single_range",
    write_segments: list[dict[str, object]] | None = None,
    final_error: RuntimeErrorInfo | None = None,
) -> PublishWriteResult:
    return PublishWriteResult(
        chunk_count=chunk_count,
        successful_chunk_count=(
            chunk_count if successful_chunk_count is None else successful_chunk_count
        ),
        written_row_count=written_row_count,
        partial_write=partial_write,
        segment_write_mode=segment_write_mode,
        write_segments=write_segments,
        final_error=final_error,
    )


class _ExtractStageStub:
    def run(self, planned_run):
        return planned_run


def _extract_stage_stub() -> _ExtractStageStub:
    return _ExtractStageStub()


def test_publish_stage_uses_failed_error_as_job_final_error_when_mixed_with_blocked(tmp_path: Path):
    workbook_path = tmp_path / "result.xlsx"
    workbook_path.write_bytes(b"placeholder")

    stage = PublishStage(
        source_reader=lambda *_args, **_kwargs: _dataset(rows=[["store-a", 100]]),
        target_loader=lambda *_args, mapping, **_kwargs: _target_context(
            previous_last_row=12,
            append_rerun_error=(
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.PUBLISH_APPEND_RERUN_BLOCKED,
                    message="Append rerun blocked",
                    retryable=False,
                )
                if mapping.mapping_id == "mapping-blocked"
                else None
            ),
        ),
        target_writer=lambda *_args, mapping, **_kwargs: _write_result(
            chunk_count=1,
            written_row_count=0,
            partial_write=True,
            final_error=(
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
                    message="Write failed",
                    retryable=False,
                )
                if mapping.mapping_id == "mapping-failed"
                else None
            ),
        ),
    )

    result = stage.run(
        PlannedPublishRun(
            batch_id="batch-001",
            job_id="job-001",
            workbook_path=workbook_path,
            mappings=[
                _mapping_spec(mapping_id="mapping-blocked", write_mode="append_rows"),
                _mapping_spec(mapping_id="mapping-failed"),
            ],
        )
    )

    assert result.status == "failed"
    assert result.manifest["final_error"]["code"] == RuntimeErrorCode.PUBLISH_WRITE_ERROR


