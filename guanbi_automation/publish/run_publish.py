from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from guanbi_automation.application.publish_runtime_service import (
    PublishRuntimeResult,
    run_publish_runtime,
)
from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode

_TENANT_ACCESS_TOKEN_ENV = "FEISHU_TENANT_ACCESS_TOKEN"


class _ArgumentParseError(Exception):
    pass


class _PublishArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentParseError(message)


def main(argv: list[str] | None = None) -> int:
    parser = _PublishArgumentParser()
    parser.add_argument("--workbook-path")
    parser.add_argument("--spec-path")
    parser.add_argument("--tenant-access-token")
    parser.add_argument("--batch-id")
    parser.add_argument("--job-id")
    try:
        args = parser.parse_args(argv)
    except _ArgumentParseError as exc:
        return _emit_result(
            PublishRuntimeResult(
                status="preflight_failed",
                batch_id="publish-cli",
                job_id="publish-parse-error",
                final_error=RuntimeErrorInfo(
                    code=RuntimeErrorCode.CONFIGURATION_ERROR,
                    message=str(exc),
                    retryable=False,
                    details={"source": "argv"},
                ),
            )
        )

    result = run_publish_runtime(
        workbook_path=Path(args.workbook_path) if args.workbook_path else None,
        spec_path=Path(args.spec_path) if args.spec_path else None,
        tenant_access_token=_resolve_tenant_access_token(args.tenant_access_token),
        batch_id=args.batch_id,
        job_id=args.job_id,
    )
    return _emit_result(result)


def _resolve_tenant_access_token(cli_value: str | None) -> str | None:
    if cli_value is not None and cli_value.strip():
        return cli_value
    env_value = os.environ.get(_TENANT_ACCESS_TOKEN_ENV)
    if env_value is not None and env_value.strip():
        return env_value
    return cli_value


def _emit_result(result: PublishRuntimeResult) -> int:
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if result.status == "completed":
        return 0
    if result.status == "preflight_failed":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
