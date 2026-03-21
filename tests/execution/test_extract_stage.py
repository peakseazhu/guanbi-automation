import httpx

from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    PollBudget,
    RequestBudget,
)
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.execution.stages.extract import ExtractStage, PlannedExtractRun


def test_extract_manifest_records_effective_runtime_profile_and_stage_metrics():
    stage = ExtractStage(sleep=lambda _seconds: None)

    result = stage.run(
        _planned_extract_run(
            template_profile="heavy",
            effective_profile="fast",
        )
    )

    assert result.status == "completed"
    assert result.manifest["template_runtime_profile"] == "heavy"
    assert result.manifest["effective_runtime_profile"] == "fast"
    assert result.manifest["submit_attempts"] >= 1
    assert result.manifest["poll_attempts"] >= 1
    assert result.manifest["download_attempts"] >= 1


def test_extract_manifest_uses_last_failed_stage_for_final_error():
    stage = ExtractStage(sleep=lambda _seconds: None)

    result = stage.run(_planned_extract_run_with_download_failure())

    assert result.status == "failed"
    assert result.manifest["download_final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR
    assert result.manifest["final_error"]["code"] == RuntimeErrorCode.NETWORK_SSL_ERROR


def test_pipeline_engine_delegates_to_extract_stage():
    stage = ExtractStage(sleep=lambda _seconds: None)
    engine = PipelineEngine(extract_stage=stage)

    result = engine.run_extract(_planned_extract_run())

    assert result.status == "completed"
    assert result.manifest["extract_id"] == "extract-001"


def _planned_extract_run(
    *,
    template_profile: str = "standard",
    effective_profile: str = "standard",
) -> PlannedExtractRun:
    return PlannedExtractRun(
        batch_id="batch-001",
        extract_id="extract-001",
        chart_id="chart-123",
        runtime_policy=_build_runtime_policy(profile_name=effective_profile),
        template_runtime_profile=template_profile,
        effective_runtime_profile=effective_profile,
        submit_request=lambda: {"task_id": "task-001"},
        fetch_status=lambda: {"task_status": "done", "download_token": "file-001"},
        download_file=lambda _payload: {"path": "downloads/file-001.xlsx"},
    )


def _planned_extract_run_with_download_failure() -> PlannedExtractRun:
    return PlannedExtractRun(
        batch_id="batch-001",
        extract_id="extract-001",
        chart_id="chart-123",
        runtime_policy=_build_runtime_policy(),
        template_runtime_profile="standard",
        effective_runtime_profile="standard",
        submit_request=lambda: {"task_id": "task-001"},
        fetch_status=lambda: {"task_status": "done", "download_token": "file-001"},
        download_file=_raise_ssl_error,
    )


def _raise_ssl_error(_payload: object) -> object:
    raise httpx.ConnectError("ssl eof")


def _build_runtime_policy(*, profile_name: str = "standard") -> ExtractRuntimePolicy:
    return ExtractRuntimePolicy(
        profile_name=profile_name,
        submit=RequestBudget(
            connect_timeout=3.0,
            read_timeout=10.0,
            max_retries=1,
        ),
        poll=PollBudget(
            poll_interval=1.0,
            max_wait=30.0,
            transient_error_retries=2,
            backoff_policy="fixed",
        ),
        download=RequestBudget(
            connect_timeout=5.0,
            read_timeout=30.0,
            max_retries=1,
        ),
        total_deadline_seconds=210.0,
    )
