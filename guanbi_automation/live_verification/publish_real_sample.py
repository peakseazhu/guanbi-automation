from __future__ import annotations

import json
import sys
from pathlib import Path

from guanbi_automation.application.live_verification_spec import (
    load_publish_live_verification_spec,
)
from guanbi_automation.application.publish_live_verification_service import (
    PublishLiveVerificationResult,
    PublishLiveVerificationService,
)


def resolve_default_spec_path(project_root: Path) -> Path:
    return Path(project_root) / "config" / "live_verification" / "publish" / "real_sample.local.yaml"


def resolve_env_path(project_root: Path) -> Path:
    root = Path(project_root)
    direct_env_path = root / ".env"
    if direct_env_path.exists():
        return direct_env_path

    if root.parent.name == ".worktrees":
        shared_env_path = root.parent.parent / ".env"
        if shared_env_path.exists():
            return shared_env_path

    return direct_env_path


def load_env_file(env_path: Path | str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(env_path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = _strip_wrapping_quotes(raw_value.strip())
    return values


def run_publish_live_verification(
    *,
    project_root: Path | None = None,
    spec_path: Path | str | None = None,
) -> PublishLiveVerificationResult:
    resolved_project_root = Path(project_root) if project_root is not None else _resolve_project_root()
    resolved_spec_path = (
        Path(spec_path)
        if spec_path is not None
        else resolve_default_spec_path(resolved_project_root)
    )
    env_values = load_env_file(resolve_env_path(resolved_project_root))
    app_id = env_values.get("FEISHU_APP_ID")
    app_secret = env_values.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise ValueError("FEISHU_APP_ID and FEISHU_APP_SECRET must exist in the resolved .env file")

    spec = load_publish_live_verification_spec(resolved_spec_path)
    service = PublishLiveVerificationService(
        app_id=app_id,
        app_secret=app_secret,
        evidence_root=resolved_project_root / "runs" / "live_verification",
    )
    return service.run(spec)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    project_root = _resolve_project_root()
    spec_path = Path(args[0]) if args else resolve_default_spec_path(project_root)

    result = run_publish_live_verification(
        project_root=project_root,
        spec_path=spec_path,
    )
    print(f"Evidence directory: {result.evidence_dir}")
    print(json.dumps(result.comparison, ensure_ascii=False, indent=2))
    return 0 if result.status == "completed" else 1


def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
