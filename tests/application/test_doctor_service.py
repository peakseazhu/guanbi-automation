from guanbi_automation.application.doctor_service import run_doctor


def test_doctor_reports_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("GUANBI_USERNAME", raising=False)

    report = run_doctor(
        required_env_vars=["GUANBI_USERNAME"],
        required_paths=[tmp_path],
        import_checks=["json"],
    )

    assert report.overall_status == "failed"
    assert report.failing_item_count >= 1
    assert any(item.status == "failed" for item in report.checks)


def test_doctor_passes_when_all_inputs_are_available(tmp_path, monkeypatch):
    manifest_path = tmp_path / "pyproject.toml"
    manifest_path.write_text(
        "[project]\n"
        "dependencies = [\n"
        '    "httpx>=0.28,<1",\n'
        "]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GUANBI_USERNAME", "tester")

    report = run_doctor(
        required_env_vars=["GUANBI_USERNAME"],
        required_paths=[tmp_path],
        import_checks=["json"],
        dependency_manifest_path=manifest_path,
    )

    assert report.overall_status == "passed"
    assert report.failing_item_count == 0
    assert all(item.status == "passed" for item in report.checks)
