from __future__ import annotations

from guanbi_automation.domain.runtime_contract import EventRecord
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode


def build_event_record(
    *,
    batch_id: str,
    stage_name: str,
    event_type: str,
    job_id: str | None = None,
    extract_id: str | None = None,
    chart_id: str | None = None,
    task_id: str | None = None,
    error_code: RuntimeErrorCode | None = None,
    attempt: int = 0,
    details: dict[str, object] | None = None,
) -> EventRecord:
    return EventRecord(
        batch_id=batch_id,
        job_id=job_id,
        extract_id=extract_id,
        stage_name=stage_name,
        chart_id=chart_id,
        task_id=task_id,
        event_type=event_type,
        error_code=error_code,
        attempt=attempt,
        details=details or {},
    )
