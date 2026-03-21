from guanbi_automation.bootstrap.container import build_runtime_contract_container
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_policy_settings_have_defaults():
    settings = RuntimePolicySettings()

    assert settings.extract.default_profile == "standard"
    assert settings.extract.profiles["heavy"].poll.max_wait == 240.0


def test_container_exposes_runtime_policy_settings():
    container = build_runtime_contract_container()

    assert isinstance(container.runtime_policy, RuntimePolicySettings)
    assert container.runtime_policy.extract.profiles["fast"].submit.connect_timeout == 3.0
