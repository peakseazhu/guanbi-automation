import csv
from pathlib import Path

from openpyxl import Workbook

from guanbi_automation.infrastructure.excel.extract_loader import load_extract_table


def test_load_extract_table_reads_first_sheet_from_xlsx(tmp_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "导出数据"
    sheet.append(["门店", "值"])
    sheet.append(["A店", 100])

    path = tmp_path / "sample.xlsx"
    workbook.save(path)

    table = load_extract_table(path)

    assert table.row_count == 2
    assert table.column_count == 2
    assert table.rows[1] == ["A店", 100]


def test_load_extract_table_supports_csv_when_requested(tmp_path: Path):
    path = tmp_path / "sample.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["区域", "值"])
        writer.writerow(["华东", "88"])

    table = load_extract_table(path)

    assert table.row_count == 2
    assert table.column_count == 2
    assert table.rows[1] == ["华东", "88"]
