from guanbi_automation.bootstrap.container import build_runtime_contract_container
from guanbi_automation.bootstrap.settings import (
    PublishSettings,
    RuntimePolicySettings,
    WorkbookSettings,
)


def test_runtime_policy_settings_have_defaults():
    settings = RuntimePolicySettings()

    assert settings.extract.default_profile == "standard"
    assert settings.extract.profiles["heavy"].poll.max_wait == 240.0


def test_container_exposes_runtime_policy_settings():
    container = build_runtime_contract_container()

    assert isinstance(container.runtime_policy, RuntimePolicySettings)
    assert container.runtime_policy.extract.profiles["fast"].submit.connect_timeout == 3.0


def test_workbook_settings_default_to_file_writer_and_positive_cell_limit():
    settings = WorkbookSettings()

    assert settings.default_writer_engine == "file"
    assert settings.cell_limit > 0


def test_publish_settings_default_to_skip_empty_sources_and_positive_chunk_limit():
    settings = PublishSettings()

    assert settings.chunk_row_limit > 0
    assert settings.empty_source_policy == "skip"


def test_publish_settings_include_column_chunk_limit():
    settings = PublishSettings()

    assert settings.chunk_row_limit > 0
    assert settings.chunk_column_limit == 100
