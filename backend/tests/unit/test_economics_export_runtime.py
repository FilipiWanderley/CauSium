from __future__ import annotations

from zipfile import ZipFile
import io

from app.domains.economics.export_runtime import build_xlsx_workbook


def test_build_xlsx_workbook_contains_expected_parts():
    workbook = build_xlsx_workbook(
        [
            ("Summary", [["key", "value"], ["current_month_cost", 123.45]]),
            ("Top Services", [["service", "cost_usd"], ["Compute", 42.0]]),
        ]
    )

    with ZipFile(io.BytesIO(workbook)) as archive:
        names = set(archive.namelist())
        assert "[Content_Types].xml" in names
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names

        sheet1 = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "current_month_cost" in sheet1
        assert "123.45" in sheet1