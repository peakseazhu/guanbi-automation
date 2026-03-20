import httpx

from guanbi_automation.domain.runtime_contract import PollingPolicy, RetryBudget, TimeoutBudget
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.pipeline_engine import PipelineEngine
from guanbi_automation.execution.stages.extract import ExtractStage, PlannedExtractRun


def test_extract_manifest_records_poll_attempts():
    stage = ExtractStage(sleep=lambda _seconds: None)
    planned_extract_run = PlannedExtractRun(
        batch_id="batch-001",
        extract_id="extract-001",
        chart_id="chart-123",
        polling_policy=_build_policy(max_wait=30.0, max_retries=3),
        fetch_status=lambda: {"task_status": "done"},
    )

    result = stage.run(planned_extract_run)

    assert result.manifest["poll_attempts"] >= 1
    assert result.manifest["runtime_policy"]["timeout_budget"]["max_wait"] == 30.0
    assert result.status == "completed"


def test_extract_stage_records_poll_timeout_as_failed_manifest():
    stage = ExtractStage(sleep=lambda _seconds: None)
    planned_extract_run = PlannedExtractRun(
        batch_id="batch-001",
        extract_id="extract-001",
        chart_id="chart-123",
        polling_policy=_build_policy(max_wait=1.5, max_retries=5),
        fetch_status=_always_timeout,
    )

    result = stage.run(planned_extract_run)

    assert result.status == "failed"
    assert result.manifest["final_error"]["code"] == RuntimeErrorCode.POLL_TIMEOUT
    assert result.manifest["poll_attempts"] >= 1
    assert result.manifest["total_wait_seconds"] == 1.5


def test_pipeline_engine_delegates_to_extract_stage():
    stage = ExtractStage(sleep=lambda _seconds: None)
    engine = PipelineEngine(extract_stage=stage)
    planned_extract_run = PlannedExtractRun(
        batch_id="batch-001",
        extract_id="extract-001",
        chart_id="chart-123",
        polling_policy=_build_policy(max_wait=30.0, max_retries=3),
        fetch_status=lambda: {"task_status": "done"},
    )

    result = engine.run_extract(planned_extract_run)

    assert result.status == "completed"
    assert result.manifest["extract_id"] == "extract-001"


def _always_timeout():
    raise httpx.ConnectTimeout("poll wait exceeded")


def _build_policy(*, max_wait: float, max_retries: int) -> PollingPolicy:
    return PollingPolicy(
        timeout_budget=TimeoutBudget(
            connect_timeout=5.0,
            read_timeout=30.0,
            poll_interval=1.0,
            max_wait=max_wait,
            max_retries=max_retries,
        ),
        retry_budget=RetryBudget(max_retries=max_retries, backoff_multiplier=2.0),
        backoff_policy="fixed",
    )
