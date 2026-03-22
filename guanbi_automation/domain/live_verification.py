from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

PublishLiveHeaderMode = Literal["include", "exclude"]
PublishLiveWriteMode = Literal["replace_sheet"]
PublishCellValue: TypeAlias = str | int | float | bool


class PublishLiveVerificationSpec(BaseModel):
    """Local-only runtime spec for a single publish live-verification run."""

    model_config = ConfigDict(frozen=True)

    workbook_path: Path
    source_sheet_name: str
    source_start_row: int = Field(ge=1)
    source_start_col: int = Field(ge=1)
    header_mode: PublishLiveHeaderMode = "include"
    spreadsheet_token: str
    sheet_id: str
    target_start_row: int = Field(ge=1)
    target_start_col: int = Field(ge=1)
    write_mode: PublishLiveWriteMode = "replace_sheet"


def canonicalize_publish_cell(value: object) -> PublishCellValue:
    """Convert workbook-origin values into JSON-safe publish payload cells."""

    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.time() == time.min:
            return value.date().isoformat()
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
