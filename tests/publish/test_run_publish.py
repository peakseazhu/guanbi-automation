from __future__ import annotations

import json
from pathlib import Path

import pytest

from guanbi_automation.application.publish_runtime_service import PublishRuntimeResult
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.publish.run_publish import main


def test_main_prints_result_envelope_and_passes_paths(monkeypatch, capsys):
    captured_kwargs: dict[str, object] = {}

    def fake_run_publish_runtime(**kwargs: object) -> PublishRuntimeResult:
        captured_kwargs.update(kwargs)
        return PublishRuntimeResult(
            status="completed",
            batch_id="publish-cli",
            job_id="publish-123456789abc",
            manifest={"stage_name": "publish"},
            final_error=None,
        )

    monkeypatch.setattr(
        "guanbi_automation.publish.run_publish.run_publish_runtime",
        fake_run_publish_runtime,
    )

    exit_code = main(
        [
            "--workbook-path",
            "result.xlsx",
            "--spec-path",
            "publish.yaml",
            "--tenant-access-token",
            "tenant-token",
            "--batch-id",
            "batch-001",
            "--job-id",
            "job-001",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "stage_name": "publish",
        "status": "completed",
        "batch_id": "publish-cli",
        "job_id": "publish-123456789abc",
        "manifest": {"stage_name": "publish"},
        "final_error": None,
    }
    assert captured_kwargs == {
        "workbook_path": Path("result.xlsx"),
        "spec_path": Path("publish.yaml"),
        "tenant_access_token": "tenant-token",
        "batch_id": "batch-001",
        "job_id": "job-001",
    }


@pytest.mark.parametrize(
    ("status", "expected_exit_code"),
    [
        ("completed", 0),
        ("preflight_failed", 2),
        ("blocked", 1),
        ("failed", 1),
    ],
)
def test_main_maps_runtime_statuses_to_exit_codes(
    monkeypatch,
    capsys,
    status: str,
    expected_exit_code: int,
):
    monkeypatch.setattr(
        "guanbi_automation.publish.run_publish.run_publish_runtime",
        lambda **_kwargs: PublishRuntimeResult(
            status=status,
            batch_id="publish-cli",
            job_id="publish-123456789abc",
            manifest=None,
            final_error=(
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.CONFIGURATION_ERROR,
                    message="bad input",
                    retryable=False,
                )
                if status != "completed"
                else None
            ),
        ),
    )

    exit_code = main(
        [
            "--workbook-path",
            "result.xlsx",
            "--spec-path",
            "publish.yaml",
            "--tenant-access-token",
            "tenant-token",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == expected_exit_code
    assert payload["status"] == status


def test_main_returns_preflight_envelope_for_missing_args(capsys):
    exit_code = main(["--spec-path", "publish.yaml"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["stage_name"] == "publish"
    assert payload["status"] == "preflight_failed"
    assert payload["manifest"] is None
    assert payload["final_error"]["code"] == RuntimeErrorCode.CONFIGURATION_ERROR


def test_main_returns_preflight_envelope_for_unknown_args(capsys):
    exit_code = main(["--bogus"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["stage_name"] == "publish"
    assert payload["status"] == "preflight_failed"
    assert payload["manifest"] is None
    assert payload["final_error"]["code"] == RuntimeErrorCode.CONFIGURATION_ERROR
    assert "--bogus" in payload["final_error"]["message"]


def test_main_reads_tenant_access_token_from_environment(monkeypatch, capsys):
    captured_kwargs: dict[str, object] = {}

    def fake_run_publish_runtime(**kwargs: object) -> PublishRuntimeResult:
        captured_kwargs.update(kwargs)
        return PublishRuntimeResult(
            status="completed",
            batch_id="publish-cli",
            job_id="publish-123456789abc",
            manifest={"stage_name": "publish"},
            final_error=None,
        )

    monkeypatch.setattr(
        "guanbi_automation.publish.run_publish.run_publish_runtime",
        fake_run_publish_runtime,
    )
    monkeypatch.setenv("FEISHU_TENANT_ACCESS_TOKEN", "env-tenant-token")

    exit_code = main(
        [
            "--workbook-path",
            "result.xlsx",
            "--spec-path",
            "publish.yaml",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "completed"
    assert captured_kwargs["tenant_access_token"] == "env-tenant-token"


def test_module_is_executable():
    source = Path("guanbi_automation/publish/run_publish.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source
