from guanbi_automation.domain.workbook_contract import WorkbookBlockSpec


def test_append_block_requires_anchor_and_locator_columns():
    block = WorkbookBlockSpec.model_validate(
        {
            "block_id": "sales_append",
            "sheet_name": "底表",
            "source_extract_id": "sales_detail",
            "write_mode": "append_rows",
            "start_row": 2,
            "start_col": 2,
            "append_locator_columns": [2, 3, 4],
            "clear_policy": "none",
        }
    )

    assert block.write_mode == "append_rows"
