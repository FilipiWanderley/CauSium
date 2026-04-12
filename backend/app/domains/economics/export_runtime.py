from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domains.cloud_accounts.service import CloudAccountService
from app.domains.cloud_ledger.service import CloudLedgerService
from app.domains.economics.models import ReportExportFormat, ReportExportJob

log = get_logger(__name__)


@dataclass
class ReportExportArtifact:
    file_name: str
    content_type: str
    content: bytes


def ensure_report_exports_dir() -> Path:
    export_dir = Path(get_settings().report_exports_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def persist_report_export_file(job_id: str, file_format: ReportExportFormat, content: bytes) -> Path:
    export_dir = ensure_report_exports_dir()
    export_path = export_dir / f"{job_id}.{file_format.value}"
    export_path.write_bytes(content)
    return export_path.resolve()


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _cell_ref(column_index: int, row_index: int) -> str:
    value = ""
    current = column_index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        value = chr(65 + remainder) + value
    return f"{value}{row_index}"


def _worksheet_xml(rows: list[list[object]]) -> str:
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row, start=1):
            ref = _cell_ref(column_index, row_index)
            if value is None:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t></t></is></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = _escape_xml(str(value))
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def build_xlsx_workbook(sheets: list[tuple[str, list[list[object]]]]) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for idx in range(1, len(sheets) + 1)
            )
            + '</Types>',
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            + "".join(
                f'<sheet name="{_escape_xml(name[:31])}" sheetId="{idx}" r:id="rId{idx}"/>'
                for idx, (name, _) in enumerate(sheets, start=1)
            )
            + '</sheets></workbook>',
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
                for idx in range(1, len(sheets) + 1)
            )
            + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            + '</Relationships>',
        )
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '</styleSheet>',
        )
        for idx, (_, rows) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _worksheet_xml(rows))
    return buffer.getvalue()


async def build_report_export_artifact(db, job: ReportExportJob) -> ReportExportArtifact:
    account_service = CloudAccountService(db)
    accounts = await account_service.list_accounts(job.org_id)
    active_accounts = sum(1 for account in accounts if account.status.value == "active")

    ledger = CloudLedgerService(db)
    dashboard = await ledger.get_dashboard_metrics(job.org_id, active_accounts)
    top_services = ledger.get_top_services(job.org_id, days=job.window_days, limit=15)
    top_teams = ledger.get_top_teams(job.org_id, days=job.window_days, limit=15)
    trend = ledger.get_cost_trend(job.org_id, days=job.window_days)

    generated_at = datetime.now(timezone.utc)
    filters_json = json.dumps(job.filters or {}, sort_keys=True)
    base_name = f"economics-{job.report_type.value}-{generated_at.strftime('%Y%m%d-%H%M%S')}"

    if job.file_format == ReportExportFormat.CSV:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["section", "key", "value"])
        writer.writerow(["metadata", "generated_at", generated_at.isoformat()])
        writer.writerow(["metadata", "window_days", job.window_days])
        writer.writerow(["metadata", "filters", filters_json])
        writer.writerow(["summary", "current_month_cost", dashboard.current_month_cost])
        writer.writerow(["summary", "previous_month_cost", dashboard.previous_month_cost])
        writer.writerow(["summary", "mom_change_pct", dashboard.mom_change_pct])
        writer.writerow(["summary", "event_count_7d", dashboard.event_count_7d])
        writer.writerow(["summary", "active_accounts", dashboard.active_accounts])
        for index, row in enumerate(top_services, start=1):
            prefix = f"top_services_{index}"
            writer.writerow([prefix, "service", row.service])
            writer.writerow([prefix, "cost_usd", row.cost_usd])
            writer.writerow([prefix, "percentage", row.percentage])
        for index, row in enumerate(top_teams, start=1):
            prefix = f"top_teams_{index}"
            writer.writerow([prefix, "team", row.service])
            writer.writerow([prefix, "cost_usd", row.cost_usd])
            writer.writerow([prefix, "percentage", row.percentage])
        for index, row in enumerate(trend, start=1):
            prefix = f"daily_trend_{index}"
            writer.writerow([prefix, "date", row.date.isoformat()])
            writer.writerow([prefix, "cost_usd", row.cost_usd])
            writer.writerow([prefix, "provider", row.provider or ""])

        content = buffer.getvalue().encode("utf-8")
        return ReportExportArtifact(
            file_name=f"{base_name}.csv",
            content_type="text/csv; charset=utf-8",
            content=content,
        )

    workbook = build_xlsx_workbook(
        [
            (
                "Summary",
                [
                    ["generated_at", generated_at.isoformat()],
                    ["window_days", job.window_days],
                    ["filters", filters_json],
                    ["current_month_cost", dashboard.current_month_cost],
                    ["previous_month_cost", dashboard.previous_month_cost],
                    ["mom_change_pct", dashboard.mom_change_pct],
                    ["event_count_7d", dashboard.event_count_7d],
                    ["active_accounts", dashboard.active_accounts],
                ],
            ),
            (
                "Top Services",
                [["service", "cost_usd", "percentage"]]
                + [[row.service, row.cost_usd, row.percentage] for row in top_services],
            ),
            (
                "Top Teams",
                [["team", "cost_usd", "percentage"]]
                + [[row.service, row.cost_usd, row.percentage] for row in top_teams],
            ),
            (
                "Daily Trend",
                [["date", "cost_usd", "provider"]]
                + [[row.date.isoformat(), row.cost_usd, row.provider or ""] for row in trend],
            ),
        ]
    )
    return ReportExportArtifact(
        file_name=f"{base_name}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=workbook,
    )