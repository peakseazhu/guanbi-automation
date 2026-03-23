from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from guanbi_automation.domain.publish_contract import PublishMappingSpec


class PublishRuntimeSpec(BaseModel):
    """Validated YAML-backed publish runtime mappings."""

    model_config = ConfigDict(frozen=True)

    mappings: list[PublishMappingSpec] = Field(min_length=1)


def load_publish_runtime_spec(spec_path: Path | str) -> PublishRuntimeSpec:
    payload = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("publish runtime spec must be a mapping")
    return PublishRuntimeSpec.model_validate(payload)
