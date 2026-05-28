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
from app.domains.decision_engine.service import DecisionEngineService
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


def _worksheet_xml(
    rows: list[list[object]],
    *,
    header_row: int = 1,
    col_formats: dict[int, int] | None = None,
) -> str:
    col_formats = col_formats or {}
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row, start=1):
            ref = _cell_ref(column_index, row_index)
            style_id = 0
            if row_index == header_row:
                style_id = 1  # bold
            elif column_index in col_formats:
                style_id = col_formats[column_index]
            if value is None:
                cells.append(f'<c r="{ref}" s="{style_id}" t="inlineStr"><is><t></t></is></c>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}" s="{style_id}"><v>{value}</v></c>')
            else:
                text = _escape_xml(str(value))
                cells.append(f'<c r="{ref}" s="{style_id}" t="inlineStr"><is><t>{text}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    freeze = ""
    if header_row >= 1:
        freeze_ref = _cell_ref(1, header_row + 1)
        freeze = (
            '<sheetViews><sheetView tabSelected="1" workbookViewId="0">'
            f'<pane ySplit="{header_row}" topLeftCell="{freeze_ref}" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'{freeze}'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


@dataclass
class SheetDef:
    name: str
    rows: list[list[object]]
    header_row: int = 1
    col_formats: dict[int, int] | None = None


def build_xlsx_workbook(sheets: list[tuple[str, list[list[object]]]] | list[SheetDef]) -> bytes:
    sheet_defs: list[SheetDef] = []
    for item in sheets:
        if isinstance(item, SheetDef):
            sheet_defs.append(item)
        else:
            name, rows = item
            sheet_defs.append(SheetDef(name=name, rows=rows))

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
                for idx in range(1, len(sheet_defs) + 1)
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
                f'<sheet name="{_escape_xml(sd.name[:31])}" sheetId="{idx}" r:id="rId{idx}"/>'
                for idx, sd in enumerate(sheet_defs, start=1)
            )
            + '</sheets></workbook>',
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>'
                for idx in range(1, len(sheet_defs) + 1)
            )
            + f'<Relationship Id="rId{len(sheet_defs) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            + '</Relationships>',
        )
        # Styles: 0=normal, 1=bold header, 2=currency ($#,##0.00), 3=percentage (0.0%)
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="2">'
            '<numFmt numFmtId="164" formatCode="&quot;$&quot;#,##0.00"/>'
            '<numFmt numFmtId="165" formatCode="0.0%"/>'
            '</numFmts>'
            '<fonts count="2">'
            '<font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            '</fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="4">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
            '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
            '</cellXfs>'
            '</styleSheet>',
        )
        for idx, sd in enumerate(sheet_defs, start=1):
            zf.writestr(
                f"xl/worksheets/sheet{idx}.xml",
                _worksheet_xml(sd.rows, header_row=sd.header_row, col_formats=sd.col_formats),
            )
    return buffer.getvalue()


_CATEGORY_LABELS = {
    "rightsizing": "Rightsizing",
    "aks_nodepool_rightsizing": "AKS Node Pool Rightsizing",
    "aks_autoscaler_recommendation": "AKS Autoscaler",
    "idle_resources": "Idle Resources",
    "reserved_instances": "Reserved Instances",
    "storage_optimization": "Storage Optimization",
    "network_optimization": "Network Optimization",
    "license_optimization": "License Optimization",
    "architecture_change": "Architecture Change",
}

_STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In Progress",
    "resolved": "Resolved",
    "dismissed": "Dismissed",
    "validated": "Validated",
}


def _format_category(raw: str) -> str:
    return _CATEGORY_LABELS.get(raw, raw.replace("_", " ").title())


def _format_status(raw: str) -> str:
    return _STATUS_LABELS.get(raw, raw.replace("_", " ").title())


async def build_report_export_artifact(db, job: ReportExportJob) -> ReportExportArtifact:
    account_service = CloudAccountService(db)
    accounts, _ = await account_service.list_accounts(job.org_id)
    active_accounts = sum(1 for account in accounts if account.status.value == "active")

    ledger = CloudLedgerService(db)
    dashboard = await ledger.get_dashboard_metrics(job.org_id, active_accounts)
    top_services, _ = ledger.get_top_services(job.org_id, days=job.window_days, limit=15)
    top_teams, _ = ledger.get_top_teams(job.org_id, days=job.window_days, limit=15)
    trend = ledger.get_cost_trend(job.org_id, days=job.window_days)

    decision_engine = DecisionEngineService(db)
    opportunities, _ = await decision_engine.list_opportunities(job.org_id, limit=50)

    total_monthly_savings = sum(op.estimated_monthly_savings_usd for op in opportunities)
    total_annual_savings = sum(op.estimated_annual_savings_usd for op in opportunities)

    generated_at = datetime.now(timezone.utc)
    filters_json = json.dumps(job.filters or {}, sort_keys=True)
    base_name = f"causium-spend-report-{generated_at.strftime('%Y%m%d-%H%M%S')}"

    if job.file_format == ReportExportFormat.CSV:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["section", "key", "value"])
        writer.writerow(["metadata", "report_title", "CauSium Spend Analysis Report"])
        writer.writerow(["metadata", "generated_at", generated_at.isoformat()])
        writer.writerow(["metadata", "window_days", job.window_days])
        writer.writerow(["metadata", "filters", filters_json])
        writer.writerow(["spend_overview", "current_period_spend_usd", round(dashboard.current_month_cost, 2)])
        writer.writerow(["spend_overview", "previous_period_spend_usd", round(dashboard.previous_month_cost, 2)])
        writer.writerow(["spend_overview", "mom_change_usd", round(dashboard.current_month_cost - dashboard.previous_month_cost, 2)])
        writer.writerow(["spend_overview", "mom_change_pct", round(dashboard.mom_change_pct, 1)])
        writer.writerow(["spend_overview", "change_events_7d", dashboard.event_count_7d])
        writer.writerow(["spend_overview", "active_cloud_accounts", dashboard.active_accounts])
        writer.writerow(["savings_summary", "total_monthly_savings_usd", round(total_monthly_savings, 2)])
        writer.writerow(["savings_summary", "annualized_savings_usd", round(total_annual_savings, 2)])
        writer.writerow(["savings_summary", "open_opportunities", len(opportunities)])
        for index, row in enumerate(top_services, start=1):
            prefix = f"spend_by_service_{index}"
            writer.writerow([prefix, "service", row.service])
            writer.writerow([prefix, "monthly_spend_usd", round(row.cost_usd, 2)])
            writer.writerow([prefix, "share_of_total_pct", round(row.percentage, 1)])
        for index, row in enumerate(top_teams, start=1):
            prefix = f"spend_by_team_{index}"
            writer.writerow([prefix, "team", row.service])
            writer.writerow([prefix, "monthly_spend_usd", round(row.cost_usd, 2)])
            writer.writerow([prefix, "share_of_total_pct", round(row.percentage, 1)])
        for index, row in enumerate(trend, start=1):
            prefix = f"daily_trend_{index}"
            writer.writerow([prefix, "date", row.date.isoformat()])
            writer.writerow([prefix, "daily_cost_usd", round(row.cost_usd, 2)])
            writer.writerow([prefix, "cloud_provider", row.provider or "All"])
        for index, op in enumerate(opportunities, start=1):
            prefix = f"opportunity_{index}"
            writer.writerow([prefix, "title", op.title])
            writer.writerow([prefix, "category", _format_category(op.category.value)])
            writer.writerow([prefix, "monthly_savings_usd", round(op.estimated_monthly_savings_usd, 2)])
            writer.writerow([prefix, "annualized_savings_usd", round(op.estimated_annual_savings_usd, 2)])
            writer.writerow([prefix, "risk_level", op.risk_level.value.capitalize()])
            writer.writerow([prefix, "effort_level", op.effort_level.value.capitalize()])
            writer.writerow([prefix, "cloud_service", op.service or ""])
            writer.writerow([prefix, "resource", op.resource_name or ""])
            writer.writerow([prefix, "region", op.region or ""])
            writer.writerow([prefix, "status", _format_status(op.status.value)])

        content = buffer.getvalue().encode("utf-8")
        return ReportExportArtifact(
            file_name=f"{base_name}.csv",
            content_type="text/csv; charset=utf-8",
            content=content,
        )

    # Style IDs: 0=normal, 1=bold, 2=currency, 3=percentage
    CURRENCY = 2
    PERCENT = 3

    workbook = build_xlsx_workbook(
        [
            SheetDef(
                name="Spend Overview",
                header_row=7,
                rows=[
                    ["CauSium — Spend Analysis Report"],
                    [],
                    ["Generated", generated_at.strftime("%Y-%m-%d %H:%M UTC")],
                    ["Report Window", f"{job.window_days} days"],
                    ["Filters", filters_json if filters_json != "{}" else "None"],
                    [],
                    ["Metric", "Value"],
                    ["Current Period Spend (USD)", round(dashboard.current_month_cost, 2)],
                    ["Previous Period Spend (USD)", round(dashboard.previous_month_cost, 2)],
                    ["Month-over-Month Change (USD)", round(dashboard.current_month_cost - dashboard.previous_month_cost, 2)],
                    ["Month-over-Month Change (%)", round(dashboard.mom_change_pct, 1)],
                    ["Active Cloud Accounts", dashboard.active_accounts],
                    ["Change Events (Last 7 Days)", dashboard.event_count_7d],
                    [],
                    ["Savings Potential", ""],
                    ["Total Monthly Savings (USD)", round(total_monthly_savings, 2)],
                    ["Annualized Savings (USD)", round(total_annual_savings, 2)],
                    ["Open Opportunities", len(opportunities)],
                ],
                col_formats={2: CURRENCY},
            ),
            SheetDef(
                name="Spend by Service",
                header_row=1,
                rows=[["Service", "Monthly Spend (USD)", "Share of Total (%)"]]
                + [[row.service, round(row.cost_usd, 2), round(row.percentage, 1)] for row in top_services],
                col_formats={2: CURRENCY, 3: PERCENT},
            ),
            SheetDef(
                name="Spend by Team",
                header_row=1,
                rows=[["Team", "Monthly Spend (USD)", "Share of Total (%)"]]
                + [[row.service, round(row.cost_usd, 2), round(row.percentage, 1)] for row in top_teams],
                col_formats={2: CURRENCY, 3: PERCENT},
            ),
            SheetDef(
                name="Daily Spend Trend",
                header_row=1,
                rows=[["Date", "Daily Cost (USD)", "Cloud Provider"]]
                + [[row.date.isoformat(), round(row.cost_usd, 2), row.provider or "All"] for row in trend],
                col_formats={2: CURRENCY},
            ),
            SheetDef(
                name="Opportunities",
                header_row=1,
                rows=[["Opportunity", "Category", "Monthly Savings (USD)", "Annualized Savings (USD)",
                       "Risk Level", "Effort Level", "Cloud Service", "Resource", "Region", "Status"]]
                + [
                    [
                        op.title,
                        _format_category(op.category.value),
                        round(op.estimated_monthly_savings_usd, 2),
                        round(op.estimated_annual_savings_usd, 2),
                        op.risk_level.value.capitalize(),
                        op.effort_level.value.capitalize(),
                        op.service or "",
                        op.resource_name or "",
                        op.region or "",
                        _format_status(op.status.value),
                    ]
                    for op in opportunities
                ],
                col_formats={3: CURRENCY, 4: CURRENCY},
            ),
            SheetDef(
                name="Recommendations",
                header_row=1,
                rows=[["Priority", "Recommendation", "Category", "Monthly Savings (USD)",
                       "Annualized Savings (USD)", "Risk Level", "Effort Level"]]
                + [
                    [
                        idx,
                        op.title,
                        _format_category(op.category.value),
                        round(op.estimated_monthly_savings_usd, 2),
                        round(op.estimated_annual_savings_usd, 2),
                        op.risk_level.value.capitalize(),
                        op.effort_level.value.capitalize(),
                    ]
                    for idx, op in enumerate(opportunities, start=1)
                ],
                col_formats={4: CURRENCY, 5: CURRENCY},
            ),
        ]
    )
    return ReportExportArtifact(
        file_name=f"{base_name}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=workbook,
    )