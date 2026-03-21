from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

WorkbookWriteMode = Literal["replace_sheet", "replace_range", "append_rows"]
WorkbookClearPolicy = Literal["none", "clear_values"]
WorkbookPostWriteActionType = Literal["fill_down_formula", "fill_fixed_value"]


class WorkbookPostWriteAction(BaseModel):
    """Declarative post-write action for a workbook block."""

    model_config = ConfigDict(frozen=True)

    action: WorkbookPostWriteActionType
    columns: list[int] = Field(default_factory=list)
    column: int | None = Field(default=None, ge=1)
    value: str | None = None


class WorkbookBlockSpec(BaseModel):
    """Bounded target block definition for workbook stage writes."""

    model_config = ConfigDict(frozen=True)

    block_id: str
    sheet_name: str
    source_extract_id: str
    write_mode: WorkbookWriteMode
    start_row: int = Field(ge=1)
    start_col: int = Field(ge=1)
    clear_policy: WorkbookClearPolicy
    end_row: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    append_locator_columns: list[int] = Field(default_factory=list)
    post_write_actions: list[WorkbookPostWriteAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_append_configuration(self) -> "WorkbookBlockSpec":
        if self.write_mode == "append_rows" and not self.append_locator_columns:
            raise ValueError("append_rows blocks must declare append_locator_columns")
        return self


class WorkbookStageSpec(BaseModel):
    """Workbook stage configuration bound to a single template workbook."""

    model_config = ConfigDict(frozen=True)

    template_path: str
    result_naming: str = "{job_id}-{run_date}.xlsx"
    blocks: list[WorkbookBlockSpec] = Field(default_factory=list)
