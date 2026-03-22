from __future__ import annotations

from guanbi_automation.bootstrap.settings import RuntimePolicySettings
from guanbi_automation.domain.runtime_contract import (
    ExtractRuntimePolicy,
    ExtractRuntimeProfileName,
)


def resolve_extract_runtime_policy(
    *,
    settings: RuntimePolicySettings,
    template_profile: ExtractRuntimeProfileName,
    override_profile: ExtractRuntimeProfileName | None = None,
) -> ExtractRuntimePolicy:
    effective_profile = override_profile or template_profile

    try:
        return settings.extract.profiles[effective_profile]
    except KeyError as exc:
        raise ValueError(f"Unknown extract runtime profile: {effective_profile}") from exc
