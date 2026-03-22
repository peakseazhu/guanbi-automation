from __future__ import annotations

from pathlib import Path

from guanbi_automation.domain.runtime_contract import StageGateDecision


def evaluate_extract_gate(
    *,
    policy: object | None,
    profile_name: str | None = None,
    available_profiles: set[str] | None = None,
) -> StageGateDecision:
    if (
        profile_name is not None
        and available_profiles is not None
        and profile_name not in available_profiles
    ):
        return StageGateDecision(
            status="blocked",
            reason="Unknown extract runtime profile",
            details={
                "profile_name": profile_name,
                "available_profiles": sorted(available_profiles),
            },
        )

    if policy is None:
        return StageGateDecision(
            status="blocked",
            reason="Missing extract runtime policy",
        )

    total_deadline = getattr(policy, "total_deadline_seconds", None)
    if total_deadline is not None and total_deadline <= 0:
        return StageGateDecision(
            status="blocked",
            reason="Extract runtime policy deadline must be positive",
            details={"total_deadline_seconds": total_deadline},
        )

    return StageGateDecision(
        status="ready",
        reason="Extract runtime policy available",
    )


def evaluate_workbook_gate(
    *,
    row_count: int,
    column_count: int,
    cell_limit: int,
    template_path: Path | str | None = None,
) -> StageGateDecision:
    if template_path is not None and not Path(template_path).exists():
        return StageGateDecision(
            status="blocked",
            reason="Workbook template is missing",
            details={"template_path": str(template_path)},
        )

    cell_count = row_count * column_count
    if cell_count > cell_limit:
        return StageGateDecision(
            status="blocked",
            reason="Workbook size guardrail triggered",
            details={
                "row_count": row_count,
                "column_count": column_count,
                "cell_count": cell_count,
                "cell_limit": cell_limit,
            },
        )

    return StageGateDecision(
        status="ready",
        reason="Workbook inputs are within guardrails",
        details={"cell_count": cell_count},
    )


def evaluate_publish_gate(
    *,
    target_ready: bool,
    workbook_path: Path | str | None = None,
    mapping_count: int = 0,
) -> StageGateDecision:
    if workbook_path is None or (
        isinstance(workbook_path, str) and not workbook_path.strip()
    ):
        return StageGateDecision(
            status="blocked",
            reason="Publish workbook is missing",
            details={"workbook_path": workbook_path},
        )

    if not Path(workbook_path).exists():
        return StageGateDecision(
            status="blocked",
            reason="Publish workbook is missing",
            details={"workbook_path": str(workbook_path)},
        )

    if mapping_count < 1:
        return StageGateDecision(
            status="blocked",
            reason="Publish mappings are missing",
            details={"mapping_count": mapping_count},
        )

    if not target_ready:
        return StageGateDecision(
            status="blocked",
            reason="Publish target is not ready",
        )

    return StageGateDecision(
        status="ready",
        reason="Publish target is ready",
    )
