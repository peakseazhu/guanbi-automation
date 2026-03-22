from __future__ import annotations

from typing import Any

import httpx

from guanbi_automation.domain.runtime_contract import RuntimeErrorInfo
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode

JSON_CONTENT_TYPE = "application/json; charset=utf-8"


class PublishClientError(Exception):
    def __init__(self, operation_name: str, error: RuntimeErrorInfo) -> None:
        super().__init__(error.message)
        self.operation_name = operation_name
        self.error = error


class FeishuSheetsClient:
    def __init__(
        self,
        *,
        base_url: str = "https://open.feishu.cn",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout)

    def query_sheets(
        self,
        spreadsheet_token: str,
        tenant_access_token: str,
    ) -> list[dict[str, object]]:
        response = self._client.get(
            f"/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query",
            headers=_auth_headers(tenant_access_token),
        )
        payload = _parse_success_payload("query_sheets", response)
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("sheets"), list):
            raise PublishClientError(
                "query_sheets",
                RuntimeErrorInfo(
                    code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
                    message="Feishu response is missing data.sheets",
                    retryable=False,
                ),
        )
        return data["sheets"]

    def fetch_tenant_access_token(
        self,
        app_id: str,
        app_secret: str,
    ) -> dict[str, Any]:
        response = self._client.post(
            "/open-apis/auth/v3/tenant_access_token/internal",
            headers=_json_headers(),
            json={
                "app_id": app_id,
                "app_secret": app_secret,
            },
        )
        return _parse_success_payload("fetch_tenant_access_token", response)

    def read_values(
        self,
        *,
        spreadsheet_token: str,
        range_string: str,
        tenant_access_token: str,
        value_render_option: str = "ToString",
        date_time_render_option: str = "FormattedString",
    ) -> dict[str, Any]:
        response = self._client.get(
            f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_string}",
            headers=_json_headers(tenant_access_token),
            params={
                "valueRenderOption": value_render_option,
                "dateTimeRenderOption": date_time_render_option,
            },
        )
        return _parse_success_payload("read_values", response)

    def write_values(
        self,
        *,
        spreadsheet_token: str,
        range_string: str,
        rows: list[list[object]],
        tenant_access_token: str,
    ) -> dict[str, Any]:
        response = self._client.put(
            f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values",
            headers=_auth_headers(tenant_access_token),
            json={"valueRange": {"range": range_string, "values": rows}},
        )
        return _parse_success_payload("write_values", response)

    def write_values_batch(
        self,
        *,
        spreadsheet_token: str,
        value_ranges: list[dict[str, object]],
        tenant_access_token: str,
    ) -> dict[str, Any]:
        response = self._client.post(
            f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_update",
            headers=_json_headers(tenant_access_token),
            json={"valueRanges": value_ranges},
        )
        return _parse_success_payload("write_values_batch", response)


def map_feishu_error(operation_name: str, response: httpx.Response) -> RuntimeErrorInfo:
    payload = _read_json_payload(response)
    feishu_code = payload.get("code") if isinstance(payload, dict) else None
    message = _resolve_error_message(response, payload)
    normalized_message = message.lower()

    error_code = RuntimeErrorCode.PUBLISH_WRITE_ERROR
    retryable = response.status_code >= 500

    if response.status_code in {401, 403} or feishu_code == 99991663:
        error_code = RuntimeErrorCode.PUBLISH_AUTH_ERROR
        retryable = False
    elif response.status_code == 429 or feishu_code == 90013:
        error_code = RuntimeErrorCode.PUBLISH_RATE_LIMIT_ERROR
        retryable = True
    elif response.status_code == 404:
        error_code = RuntimeErrorCode.PUBLISH_TARGET_MISSING
        retryable = False
    elif operation_name in {"write_values", "write_values_batch", "read_values"} and (
        response.status_code == 400 or "range" in normalized_message
    ):
        error_code = RuntimeErrorCode.PUBLISH_RANGE_INVALID
        retryable = False

    details: dict[str, object] = {
        "operation_name": operation_name,
        "status_code": response.status_code,
    }
    if feishu_code is not None:
        details["feishu_code"] = feishu_code

    return RuntimeErrorInfo(
        code=error_code,
        message=message,
        retryable=retryable,
        details=details,
    )


def _auth_headers(tenant_access_token: str) -> dict[str, str]:
    return _json_headers(tenant_access_token)


def _json_headers(tenant_access_token: str | None = None) -> dict[str, str]:
    headers = {"Content-Type": JSON_CONTENT_TYPE}
    if tenant_access_token:
        headers["Authorization"] = f"Bearer {tenant_access_token}"
    return headers


def _parse_success_payload(operation_name: str, response: httpx.Response) -> dict[str, Any]:
    payload = _read_json_payload(response)
    payload_code = payload.get("code") if isinstance(payload, dict) else None

    if response.is_error or payload_code not in {None, 0}:
        raise PublishClientError(operation_name, map_feishu_error(operation_name, response))
    if not isinstance(payload, dict):
        raise PublishClientError(
            operation_name,
            RuntimeErrorInfo(
                code=RuntimeErrorCode.PUBLISH_WRITE_ERROR,
                message="Feishu response payload must be a JSON object",
                retryable=False,
            ),
        )
    return payload


def _read_json_payload(response: httpx.Response) -> dict[str, Any] | list[Any] | None:
    try:
        return response.json()
    except ValueError:
        return None


def _resolve_error_message(
    response: httpx.Response,
    payload: dict[str, Any] | list[Any] | None,
) -> str:
    if isinstance(payload, dict):
        raw_message = payload.get("msg")
        if isinstance(raw_message, str) and raw_message.strip():
            return raw_message

    text = response.text.strip()
    if text:
        return text
    return f"Feishu {response.status_code} error"
