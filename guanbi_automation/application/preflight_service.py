from __future__ import annotations

from typing import Any

from guanbi_automation.domain.runtime_contract import StageGateDecision
from guanbi_automation.execution.stage_gates import (
    evaluate_extract_gate,
    evaluate_publish_gate,
    evaluate_workbook_gate,
)


def run_stage_preflight(stage_name: str, **kwargs: Any) -> StageGateDecision:
    if stage_name == "extract":
        return evaluate_extract_gate(
            policy=kwargs.get("policy"),
            profile_name=kwargs.get("profile_name"),
            available_profiles=kwargs.get("available_profiles"),
        )
    if stage_name == "workbook":
        return evaluate_workbook_gate(
            row_count=kwargs.get("row_count", 0),
            column_count=kwargs.get("column_count", 0),
            cell_limit=kwargs["cell_limit"],
            template_path=kwargs.get("template_path"),
        )
    if stage_name == "publish":
        return evaluate_publish_gate(target_ready=kwargs.get("target_ready", False))

    return StageGateDecision(
        status="blocked",
        reason=f"Unsupported stage: {stage_name}",
    )
