from guanbi_automation.bootstrap.container import build_runtime_contract_container
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_policy_settings_have_defaults():
    settings = RuntimePolicySettings()

    assert settings.extract_polling.max_retries >= 0
    assert settings.extract_polling.poll_interval > 0


def test_container_exposes_runtime_policy_settings():
    container = build_runtime_contract_container()

    assert isinstance(container.runtime_policy, RuntimePolicySettings)
    assert container.runtime_policy.extract_polling.max_wait > 0
