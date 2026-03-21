from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guanbi_automation.application.preflight_service import run_stage_preflight
from guanbi_automation.bootstrap.settings import WorkbookSettings
from guanbi_automation.domain.workbook_contract import WorkbookStageSpec
from guanbi_automation.execution.manifest_builder import build_workbook_manifest
from guanbi_automation.infrastructure.excel.extract_loader import load_extract_table
from guanbi_automation.infrastructure.excel.workbook_writer import write_block


@dataclass(frozen=True)
class PlannedWorkbookIngestRun:
    batch_id: str
    job_id: str
    workbook_spec: WorkbookStageSpec
    result_path: Path
    extract_artifacts: dict[str, Path]
    workbook_settings: WorkbookSettings


@dataclass(frozen=True)
class WorkbookIngestStageResult:
    status: str
    manifest: dict[str, Any]
    workbook_path: Path | None = None


class WorkbookIngestStage:
    """Loads extract artifacts and writes bounded workbook blocks."""

    def run(self, planned_run: PlannedWorkbookIngestRun) -> WorkbookIngestStageResult:
        blocks: list[dict[str, Any]] = []

        for block in planned_run.workbook_spec.blocks:
            artifact_path = planned_run.extract_artifacts[block.source_extract_id]
            table = load_extract_table(artifact_path)
            gate = run_stage_preflight(
                stage_name="workbook",
                row_count=table.row_count,
                column_count=table.column_count,
                cell_limit=planned_run.workbook_settings.cell_limit,
                template_path=planned_run.workbook_spec.template_path,
            )
            block_manifest = {
                "block_id": block.block_id,
                "source_extract_id": block.source_extract_id,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cell_count": table.cell_count,
                "gate": gate.model_dump(mode="json"),
            }
            if gate.status != "ready":
                blocks.append(block_manifest)
                manifest = build_workbook_manifest(
                    batch_id=planned_run.batch_id,
                    job_id=planned_run.job_id,
                    stage_name="workbook_ingest",
                    template_path=planned_run.workbook_spec.template_path,
                    result_path=str(planned_run.result_path),
                    blocks=blocks,
                    completed=False,
                )
                return WorkbookIngestStageResult(status="blocked", manifest=manifest)

            write_result = write_block(
                template_path=Path(planned_run.workbook_spec.template_path),
                result_path=planned_run.result_path,
                block=block,
                rows=table.rows,
            )
            block_manifest.update(
                {
                    "written_start_row": write_result.written_start_row,
                    "written_end_row": write_result.written_end_row,
                    "written_start_col": write_result.written_start_col,
                    "written_end_col": write_result.written_end_col,
                    "actions": write_result.actions,
                }
            )
            blocks.append(block_manifest)

        manifest = build_workbook_manifest(
            batch_id=planned_run.batch_id,
            job_id=planned_run.job_id,
            stage_name="workbook_ingest",
            template_path=planned_run.workbook_spec.template_path,
            result_path=str(planned_run.result_path),
            blocks=blocks,
            completed=True,
        )
        return WorkbookIngestStageResult(
            status="completed",
            manifest=manifest,
            workbook_path=planned_run.result_path,
        )
