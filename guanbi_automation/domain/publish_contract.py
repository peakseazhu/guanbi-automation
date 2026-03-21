from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PublishReadMode = Literal["sheet", "block"]
PublishWriteMode = Literal["replace_sheet", "replace_range", "append_rows"]
PublishHeaderMode = Literal["exclude", "include"]


class PublishSourceSpec(BaseModel):
    """Bounded workbook source definition for publish stage reads."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    sheet_name: str
    read_mode: PublishReadMode
    start_row: int = Field(ge=1)
    start_col: int = Field(ge=1)
    end_row: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    header_mode: PublishHeaderMode = "exclude"


class PublishTargetSpec(BaseModel):
    """Bounded Feishu target definition for publish stage writes."""

    model_config = ConfigDict(frozen=True)

    spreadsheet_token: str
    sheet_id: str | None = None
    sheet_name: str | None = None
    write_mode: PublishWriteMode
    start_row: int = Field(ge=1)
    start_col: int = Field(ge=1)
    end_row: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    append_locator_columns: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_append_configuration(self) -> "PublishTargetSpec":
        has_sheet_id = bool(self.sheet_id and self.sheet_id.strip())
        has_sheet_name = bool(self.sheet_name and self.sheet_name.strip())
        if not has_sheet_id and not has_sheet_name:
            raise ValueError("publish targets must declare sheet_id or sheet_name")
        if self.write_mode == "append_rows" and not self.append_locator_columns:
            raise ValueError("append_rows targets must declare append_locator_columns")
        return self
