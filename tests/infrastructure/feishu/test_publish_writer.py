import json

import httpx

from guanbi_automation.domain.publish_contract import (
    PublishDataset,
    PublishMappingSpec,
    PublishSourceSpec,
    PublishTargetSpec,
)
from guanbi_automation.domain.runtime_errors import RuntimeErrorCode
from guanbi_automation.execution.stages.publish import PublishTargetContext
from guanbi_automation.infrastructure.feishu.client import FeishuSheetsClient
from guanbi_automation.infrastructure.feishu.publish_writer import write_publish_target
from guanbi_automation.infrastructure.feishu.target_planner import ResolvedPublishTarget


def test_write_publish_target_uses_single_range_for_small_dataset():
    requests: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            (
                request.method,
                request.url.path,
                json.loads(request.content.decode("utf-8")),
            )
        )
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": {"updatedRange": "ySyhcD!B3:C4"}},
        )

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[["x", 1], ["y", 2]],
            row_count=2,
            column_count=2,
            source_range="计算表1!A2:B3",
        ),
        target_context=_target_context(),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests == [
        (
            "PUT",
            "/open-apis/sheets/v2/spreadsheets/sheet-token/values",
            {
                "valueRange": {
                    "range": "ySyhcD!B3:C4",
                    "values": [["x", 1], ["y", 2]],
                }
            },
        )
    ]
    assert result.chunk_count == 1
    assert result.successful_chunk_count == 1
    assert result.written_row_count == 2
    assert result.partial_write is False
    assert result.segment_write_mode == "single_range"
    assert result.write_segments == [
        {
            "range_string": "ySyhcD!B3:C4",
            "row_count": 2,
            "column_count": 2,
            "row_offset": 0,
            "column_offset": 0,
        }
    ]
    assert result.events == [
        {
            "event": "publish_target_write_completed",
            "operation": "write_values",
            "segment_count": 1,
            "segment_write_mode": "single_range",
        }
    ]


def test_write_publish_target_honors_explicit_target_rectangle_and_pads_missing_cells():
    requests: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            (
                request.method,
                request.url.path,
                json.loads(request.content.decode("utf-8")),
            )
        )
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": {"updatedRange": "ySyhcD!B3:E5"}},
        )

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[["x", 1], ["y", 2]],
            row_count=2,
            column_count=2,
            source_range="计算表1!A2:B3",
        ),
        target_context=PublishTargetContext(
            resolved_target=ResolvedPublishTarget(
                sheet_id="ySyhcD",
                sheet_title="子表1",
                range_string="子表1!B3:E5",
                start_row=3,
                start_col=2,
                end_row=5,
                end_col=5,
            )
        ),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests == [
        (
            "PUT",
            "/open-apis/sheets/v2/spreadsheets/sheet-token/values",
            {
                "valueRange": {
                    "range": "ySyhcD!B3:E5",
                    "values": [
                        ["x", 1, "", ""],
                        ["y", 2, "", ""],
                        ["", "", "", ""],
                    ],
                }
            },
        )
    ]
    assert result.chunk_count == 1
    assert result.successful_chunk_count == 1
    assert result.written_row_count == 2
    assert result.partial_write is False
    assert result.segment_write_mode == "single_range"
    assert result.write_segments == [
        {
            "range_string": "ySyhcD!B3:E5",
            "row_count": 3,
            "column_count": 4,
            "row_offset": 0,
            "column_offset": 0,
        }
    ]


def test_write_publish_target_uses_batch_ranges_for_wide_dataset():
    requests: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            (
                request.method,
                request.url.path,
                json.loads(request.content.decode("utf-8")),
            )
        )
        return httpx.Response(
            200,
            json={"code": 0, "msg": "ok", "data": {"responses": [{"updatedRange": "x"}]}},
        )

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[[f"col-{index}" for index in range(127)]],
            row_count=1,
            column_count=127,
            source_range="计算表1!A2:DW2",
        ),
        target_context=PublishTargetContext(
            resolved_target=ResolvedPublishTarget(
                sheet_id="ySyhcD",
                sheet_title="子表1",
                range_string="子表1!B3:DX3",
                start_row=3,
                start_col=2,
                end_row=3,
                end_col=128,
            )
        ),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests == [
        (
            "POST",
            "/open-apis/sheets/v2/spreadsheets/sheet-token/values_batch_update",
            {
                "valueRanges": [
                    {
                        "range": "ySyhcD!B3:CW3",
                        "values": [[f"col-{index}" for index in range(100)]],
                    },
                    {
                        "range": "ySyhcD!CX3:DX3",
                        "values": [[f"col-{index}" for index in range(100, 127)]],
                    },
                ]
            },
        )
    ]
    assert result.chunk_count == 1
    assert result.successful_chunk_count == 1
    assert result.written_row_count == 1
    assert result.partial_write is False
    assert result.segment_write_mode == "batch_ranges"
    assert [segment["column_count"] for segment in result.write_segments] == [100, 27]
    assert result.events == [
        {
            "event": "publish_target_write_completed",
            "operation": "write_values_batch",
            "segment_count": 2,
            "segment_write_mode": "batch_ranges",
        }
    ]


def test_write_publish_target_slices_tall_wide_dataset_in_row_major_batch_order():
    requests: list[tuple[str, str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            (
                request.method,
                request.url.path,
                json.loads(request.content.decode("utf-8")),
            )
        )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": "ok",
                "data": {"responses": [{"updatedRange": "x"} for _ in range(4)]},
            },
        )

    rows = [
        [f"r{row_index}-c{column_index}" for column_index in range(127)]
        for row_index in range(520)
    ]
    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=rows,
            row_count=520,
            column_count=127,
            source_range="计算表1!A2:DW521",
        ),
        target_context=PublishTargetContext(
            resolved_target=ResolvedPublishTarget(
                sheet_id="ySyhcD",
                sheet_title="子表1",
                range_string="子表1!B5:DX524",
                start_row=5,
                start_col=2,
                end_row=524,
                end_col=128,
            )
        ),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert requests[0][0:2] == (
        "POST",
        "/open-apis/sheets/v2/spreadsheets/sheet-token/values_batch_update",
    )
    payload = requests[0][2]
    assert [value_range["range"] for value_range in payload["valueRanges"]] == [
        "ySyhcD!B5:CW504",
        "ySyhcD!CX5:DX504",
        "ySyhcD!B505:CW524",
        "ySyhcD!CX505:DX524",
    ]
    assert payload["valueRanges"][0]["values"][0][0] == "r0-c0"
    assert payload["valueRanges"][1]["values"][0][0] == "r0-c100"
    assert payload["valueRanges"][2]["values"][0][0] == "r500-c0"
    assert payload["valueRanges"][3]["values"][0][0] == "r500-c100"
    assert payload["valueRanges"][3]["values"][-1][-1] == "r519-c126"
    assert [segment["row_offset"] for segment in result.write_segments] == [0, 0, 500, 500]
    assert [segment["column_offset"] for segment in result.write_segments] == [0, 100, 0, 100]
    assert result.segment_write_mode == "batch_ranges"
    assert result.chunk_count == 1
    assert result.successful_chunk_count == 1
    assert result.written_row_count == 520


def test_write_publish_target_returns_failed_result_when_client_write_raises():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": 123400, "msg": "invalid range"})

    result = write_publish_target(
        mapping=_mapping_spec(),
        dataset=PublishDataset(
            rows=[["x", 1], ["y", 2]],
            row_count=2,
            column_count=2,
            source_range="计算表1!A2:B3",
        ),
        target_context=_target_context(),
        client=FeishuSheetsClient(transport=httpx.MockTransport(handler)),
        tenant_access_token="tenant-token",
        chunk_row_limit=500,
        chunk_column_limit=100,
    )

    assert result.chunk_count == 1
    assert result.successful_chunk_count == 0
    assert result.written_row_count == 0
    assert result.partial_write is False
    assert result.segment_write_mode == "single_range"
    assert result.write_segments == [
        {
            "range_string": "ySyhcD!B3:C4",
            "row_count": 2,
            "column_count": 2,
            "row_offset": 0,
            "column_offset": 0,
        }
    ]
    assert result.final_error is not None
    assert result.final_error.code == RuntimeErrorCode.PUBLISH_RANGE_INVALID
    assert result.events == [
        {
            "event": "publish_target_write_failed",
            "operation": "write_values",
            "segment_count": 1,
            "segment_write_mode": "single_range",
            "error_code": RuntimeErrorCode.PUBLISH_RANGE_INVALID.value,
        }
    ]


def _mapping_spec() -> PublishMappingSpec:
    return PublishMappingSpec(
        mapping_id="mapping-001",
        source=PublishSourceSpec(
            source_id="calc-1",
            sheet_name="计算表1",
            read_mode="sheet",
            start_row=2,
            start_col=1,
        ),
        target=PublishTargetSpec(
            spreadsheet_token="sheet-token",
            sheet_id="ySyhcD",
            write_mode="replace_range",
            start_row=3,
            start_col=2,
        ),
    )


def _target_context(*, end_col: int = 3) -> PublishTargetContext:
    return PublishTargetContext(
        resolved_target=ResolvedPublishTarget(
            sheet_id="ySyhcD",
            sheet_title="子表1",
            range_string="子表1!B3:C4",
            start_row=3,
            start_col=2,
            end_row=4,
            end_col=end_col,
        )
    )
