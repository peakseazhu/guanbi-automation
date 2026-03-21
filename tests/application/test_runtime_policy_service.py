from guanbi_automation.application.runtime_policy_service import (
    resolve_extract_runtime_policy,
)
from guanbi_automation.bootstrap.settings import RuntimePolicySettings


def test_runtime_profile_override_wins_over_template_default():
    settings = RuntimePolicySettings()

    policy = resolve_extract_runtime_policy(
        settings=settings,
        template_profile="heavy",
        override_profile="fast",
    )

    assert policy.profile_name == "fast"
    assert policy.poll.max_wait == 45.0
