from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Iterable

from guanbi_automation.bootstrap.dependency_manifest import load_dependency_manifest
from guanbi_automation.domain.runtime_contract import DoctorCheckResult, DoctorReport


def run_doctor(
    *,
    required_env_vars: Iterable[str],
    required_paths: Iterable[Path | str],
    import_checks: Iterable[str],
    dependency_manifest_path: Path | str | None = None,
    minimum_python: tuple[int, int] = (3, 12),
) -> DoctorReport:
    checks = [
        _check_python_version(minimum_python),
        *_check_imports(import_checks),
        *_check_env_vars(required_env_vars),
        *_check_paths(required_paths),
        _check_dependency_manifest(dependency_manifest_path),
    ]
    failing_count = sum(1 for item in checks if item.status == "failed")

    return DoctorReport(
        overall_status="failed" if failing_count else "passed",
        checks=checks,
        failing_item_count=failing_count,
    )


def _check_python_version(minimum_python: tuple[int, int]) -> DoctorCheckResult:
    current = sys.version_info[:3]
    status = "passed" if current >= minimum_python else "failed"
    detail = (
        f"Detected Python {current[0]}.{current[1]}.{current[2]}; "
        f"requires >= {minimum_python[0]}.{minimum_python[1]}"
    )
    return DoctorCheckResult(name="python_version", status=status, detail=detail)


def _check_imports(import_checks: Iterable[str]) -> list[DoctorCheckResult]:
    results: list[DoctorCheckResult] = []
    for module_name in import_checks:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            results.append(
                DoctorCheckResult(
                    name=f"import:{module_name}",
                    status="failed",
                    detail=str(exc),
                )
            )
        else:
            results.append(
                DoctorCheckResult(
                    name=f"import:{module_name}",
                    status="passed",
                    detail="import available",
                )
            )
    return results


def _check_env_vars(required_env_vars: Iterable[str]) -> list[DoctorCheckResult]:
    results: list[DoctorCheckResult] = []
    for var_name in required_env_vars:
        status = "passed" if os.getenv(var_name) else "failed"
        detail = "set" if status == "passed" else "missing"
        results.append(
            DoctorCheckResult(
                name=f"env:{var_name}",
                status=status,
                detail=detail,
            )
        )
    return results


def _check_paths(required_paths: Iterable[Path | str]) -> list[DoctorCheckResult]:
    results: list[DoctorCheckResult] = []
    for raw_path in required_paths:
        path = Path(raw_path)
        exists = path.exists()
        writable = os.access(path, os.W_OK) if exists else False
        status = "passed" if exists and writable else "failed"
        detail = f"exists={exists}, writable={writable}"
        results.append(
            DoctorCheckResult(
                name=f"path:{path}",
                status=status,
                detail=detail,
            )
        )
    return results


def _check_dependency_manifest(
    dependency_manifest_path: Path | str | None,
) -> DoctorCheckResult:
    manifest_path = Path(dependency_manifest_path or "pyproject.toml")
    try:
        manifest = load_dependency_manifest(manifest_path)
    except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
        return DoctorCheckResult(
            name="dependency_manifest",
            status="failed",
            detail=str(exc),
        )

    detail = f"{manifest.source_path} ({len(manifest.dependencies)} dependencies)"
    return DoctorCheckResult(
        name="dependency_manifest",
        status="passed",
        detail=detail,
    )
