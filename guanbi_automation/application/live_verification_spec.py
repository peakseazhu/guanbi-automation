from __future__ import annotations

from pathlib import Path

import yaml

from guanbi_automation.domain.live_verification import PublishLiveVerificationSpec


def load_publish_live_verification_spec(
    spec_path: Path | str,
) -> PublishLiveVerificationSpec:
    resolved_path = Path(spec_path)
    payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("publish live verification spec must be a mapping")
    return PublishLiveVerificationSpec.model_validate(payload)
