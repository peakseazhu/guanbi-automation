import json

import httpx
import pytest

from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.infrastructure.feishu.client import (
    FeishuSheetsClient,
    PublishClientError,
    map_feishu_error,
)


def test_map_feishu_401_to_publish_auth_error():
    response = httpx.Response(401, json={"code": 99991663, "msg": "Auth failed"})

    error = map_feishu_error("query_sheets", response)

    assert error.code == RuntimeErrorCode.PUBLISH_AUTH_ERROR
    assert error.retryable is False


def test_map_feishu_rate_limit_to_retryable_publish_error():
    response = httpx.Response(429, json={"code": 90013, "msg": "rate limit"})

    error = map_feishu_error("write_values", response)

    assert error.code == RuntimeErrorCode.PUBLISH_RATE_LIMIT_ERROR
    assert error.retryable is True


def test_map_feishu_write_range_error_to_publish_range_invalid():
    response = httpx.Response(400, json={"code": 123400, "msg": "invalid range"})

    error = map_feishu_error("write_values", response)

    assert error.code == RuntimeErrorCode.PUBLISH_RANGE_INVALID
    assert error.retryable is False


def test_query_sheets_returns_sheet_metadata_and_uses_auth_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/open-apis/sheets/v3/spreadsheets/spreadsheet-token/sheets/query"
        assert request.headers["Authorization"] == "Bearer tenant-token"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "success",
                "data": {
                    "sheets": [
                        {"sheet_id": "sheet-1", "title": "子表1"},
                        {"sheet_id": "sheet-2", "title": "子表2"},
                    ]
                },
            },
        )

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    sheets = client.query_sheets("spreadsheet-token", "tenant-token")

    assert sheets == [
        {"sheet_id": "sheet-1", "title": "子表1"},
        {"sheet_id": "sheet-2", "title": "子表2"},
    ]


def test_query_sheets_raises_publish_client_error_on_http_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": 99991663, "msg": "Auth failed"})

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    with pytest.raises(PublishClientError) as exc_info:
        client.query_sheets("spreadsheet-token", "tenant-token")

    assert exc_info.value.error.code == RuntimeErrorCode.PUBLISH_AUTH_ERROR


def test_fetch_tenant_access_token_posts_app_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/open-apis/auth/v3/tenant_access_token/internal"
        assert request.headers["Content-Type"] == "application/json; charset=utf-8"
        assert json.loads(request.content.decode("utf-8")) == {
            "app_id": "app-id",
            "app_secret": "app-secret",
        }
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "ok",
                "tenant_access_token": "tenant-token",
                "expire": 7200,
            },
        )

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    payload = client.fetch_tenant_access_token("app-id", "app-secret")

    assert payload["tenant_access_token"] == "tenant-token"
    assert payload["expire"] == 7200


def test_write_values_sends_value_range_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/open-apis/sheets/v2/spreadsheets/spreadsheet-token/values"
        assert request.headers["Authorization"] == "Bearer tenant-token"
        assert json.loads(request.content.decode("utf-8")) == {
            "valueRange": {
                "range": "子表1!B3:C4",
                "values": [["x", 1], ["y", 2]],
            }
        }
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "success",
                "data": {"updatedRange": "子表1!B3:C4", "updatedRows": 2},
            },
        )

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    payload = client.write_values(
        spreadsheet_token="spreadsheet-token",
        range_string="子表1!B3:C4",
        rows=[["x", 1], ["y", 2]],
        tenant_access_token="tenant-token",
    )

    assert payload["data"]["updatedRows"] == 2


def test_read_values_requests_single_range_with_render_options():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/open-apis/sheets/v2/spreadsheets/spreadsheet-token/values/ySyhcD!A1:CV80"
        assert request.headers["Authorization"] == "Bearer tenant-token"
        assert request.headers["Content-Type"] == "application/json; charset=utf-8"
        assert request.url.params["valueRenderOption"] == "ToString"
        assert request.url.params["dateTimeRenderOption"] == "FormattedString"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "success",
                "data": {
                    "revision": 7,
                    "spreadsheetToken": "spreadsheet-token",
                    "valueRange": {
                        "majorDimension": "ROWS",
                        "range": "ySyhcD!A1:CV80",
                        "revision": 7,
                        "values": [["表头1", "表头2"], ["x", "1"]],
                    },
                },
            },
        )

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    payload = client.read_values(
        spreadsheet_token="spreadsheet-token",
        range_string="ySyhcD!A1:CV80",
        tenant_access_token="tenant-token",
    )

    assert payload["data"]["valueRange"]["values"] == [["表头1", "表头2"], ["x", "1"]]


def test_write_values_batch_sends_multiple_ranges_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/open-apis/sheets/v2/spreadsheets/spreadsheet-token/values_batch_update"
        assert request.headers["Authorization"] == "Bearer tenant-token"
        assert request.headers["Content-Type"] == "application/json; charset=utf-8"
        assert json.loads(request.content.decode("utf-8")) == {
            "valueRanges": [
                {
                    "range": "ySyhcD!A1:CV80",
                    "values": [["表头1", "表头2"], ["x", "1"]],
                },
                {
                    "range": "ySyhcD!CW1:DW80",
                    "values": [["表头101", "表头127"], ["a", "b"]],
                },
            ]
        }
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "success",
                "data": {
                    "revision": 88,
                    "spreadsheetToken": "spreadsheet-token",
                    "responses": [
                        {
                            "updatedRange": "ySyhcD!A1:CV80",
                            "updatedRows": 80,
                            "updatedColumns": 100,
                            "updatedCells": 8000,
                        },
                        {
                            "updatedRange": "ySyhcD!CW1:DW80",
                            "updatedRows": 80,
                            "updatedColumns": 27,
                            "updatedCells": 2160,
                        },
                    ],
                },
            },
        )

    client = FeishuSheetsClient(transport=httpx.MockTransport(handler))

    payload = client.write_values_batch(
        spreadsheet_token="spreadsheet-token",
        value_ranges=[
            {
                "range": "ySyhcD!A1:CV80",
                "values": [["表头1", "表头2"], ["x", "1"]],
            },
            {
                "range": "ySyhcD!CW1:DW80",
                "values": [["表头101", "表头127"], ["a", "b"]],
            },
        ],
        tenant_access_token="tenant-token",
    )

    assert payload["data"]["responses"][1]["updatedColumns"] == 27
