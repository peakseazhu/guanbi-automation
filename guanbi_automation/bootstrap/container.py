from __future__ import annotations

from dataclasses import dataclass

from guanbi_automation.bootstrap.settings import RuntimePolicySettings


@dataclass(frozen=True)
class RuntimeContractContainer:
    runtime_policy: RuntimePolicySettings


def build_runtime_contract_container(
    settings: RuntimePolicySettings | None = None,
) -> RuntimeContractContainer:
    return RuntimeContractContainer(runtime_policy=settings or RuntimePolicySettings())
