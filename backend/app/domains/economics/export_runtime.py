from __future__ import annotations

import csv
import io
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

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

    # --- XLSX via openpyxl ---
    from app.domains.gov.service import GovService
    from app.domains.green.service import GreenService

    gov = GovService()
    gov_summary = gov.get_summary(job.org_id, days=job.window_days)
    gov_unowned = gov.get_unowned_costs(job.org_id, days=job.window_days, limit=30)
    gov_compliance = gov.get_label_compliance(job.org_id, days=job.window_days)

    green = GreenService()
    green_summary = green.get_summary(job.org_id, months=6)
    green_monthly = green.get_emissions_monthly(job.org_id, months=6)

    workbook_bytes = _build_enterprise_xlsx(
        dashboard=dashboard,
        top_services=top_services,
        top_teams=top_teams,
        trend=trend,
        opportunities=opportunities,
        total_monthly_savings=total_monthly_savings,
        total_annual_savings=total_annual_savings,
        gov_summary=gov_summary,
        gov_unowned=gov_unowned,
        gov_compliance=gov_compliance,
        green_summary=green_summary,
        green_monthly=green_monthly,
        generated_at=generated_at,
        window_days=job.window_days,
        filters_json=filters_json,
    )
    return ReportExportArtifact(
        file_name=f"{base_name}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=workbook_bytes,
    )


# ---------------------------------------------------------------------------
# Styling constants
# ---------------------------------------------------------------------------

_BRAND_DARK = "1B2A4A"
_BRAND_ACCENT = "2E86AB"
_ROW_ALT = "F0F6FC"
_HEADER_FILL = PatternFill(start_color=_BRAND_DARK, end_color=_BRAND_DARK, fill_type="solid")
_ALT_FILL = PatternFill(start_color=_ROW_ALT, end_color=_ROW_ALT, fill_type="solid")
_HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
_TITLE_FONT = Font(name="Calibri", bold=True, color=_BRAND_DARK, size=16)
_SUBTITLE_FONT = Font(name="Calibri", bold=True, color=_BRAND_DARK, size=12)
_KPI_VALUE_FONT = Font(name="Calibri", bold=True, size=14)
_KPI_LABEL_FONT = Font(name="Calibri", color="555555", size=10)
_THIN_BORDER = Border(
    left=Side(style="thin", color="D0D0D0"),
    right=Side(style="thin", color="D0D0D0"),
    top=Side(style="thin", color="D0D0D0"),
    bottom=Side(style="thin", color="D0D0D0"),
)
_BRL_FORMAT = 'R$ #,##0.00'
_PCT_FORMAT = '0.0%'
_DATE_FORMAT = 'DD/MM/YYYY'


def _auto_width(ws, min_width: int = 10, max_width: int = 45) -> None:
    for col_cells in ws.columns:
        length = min_width
        for cell in col_cells:
            if cell.value is not None:
                length = max(length, min(len(str(cell.value)) + 2, max_width))
        ws.column_dimensions[get_column_letter(col_cells[0].column)].width = length


def _write_table_header(ws, row: int, headers: list[str]) -> None:
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _THIN_BORDER


def _apply_table_style(ws, start_row: int, end_row: int, num_cols: int, currency_cols: list[int] | None = None, pct_cols: list[int] | None = None) -> None:
    currency_cols = currency_cols or []
    pct_cols = pct_cols or []
    for r in range(start_row, end_row + 1):
        for c in range(1, num_cols + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = _THIN_BORDER
            cell.alignment = Alignment(vertical="center")
            if c in currency_cols:
                cell.number_format = _BRL_FORMAT
            elif c in pct_cols:
                cell.number_format = _PCT_FORMAT
            if (r - start_row) % 2 == 1:
                # Don't overwrite cells that already have a meaningful fill (e.g. risk colors)
                if not cell.fill or not cell.fill.start_color or cell.fill.start_color.rgb in (None, "00000000"):
                    cell.fill = _ALT_FILL


def _build_enterprise_xlsx(
    *,
    dashboard,
    top_services,
    top_teams,
    trend,
    opportunities,
    total_monthly_savings: float,
    total_annual_savings: float,
    gov_summary,
    gov_unowned,
    gov_compliance,
    green_summary,
    green_monthly,
    generated_at: datetime,
    window_days: int,
    filters_json: str,
) -> bytes:
    wb = Workbook()

    # --- Sheet 1: Resumo Executivo ---
    ws = wb.active
    ws.title = "Resumo Executivo"
    _build_executive_summary(
        ws, dashboard, top_services, top_teams, opportunities,
        total_monthly_savings, total_annual_savings,
        generated_at, window_days, filters_json,
    )

    # --- Sheet 2: Custos ---
    ws2 = wb.create_sheet("Custos")
    _build_costs_sheet(ws2, top_services, top_teams, trend)

    # --- Sheet 3: Oportunidades ---
    ws3 = wb.create_sheet("Oportunidades")
    _build_opportunities_sheet(ws3, opportunities, total_monthly_savings, total_annual_savings)

    # --- Sheet 4: Governança ---
    ws4 = wb.create_sheet("Governança")
    _build_governance_sheet(ws4, gov_summary, gov_unowned, gov_compliance)

    # --- Sheet 5: Sustentabilidade ---
    ws5 = wb.create_sheet("Sustentabilidade")
    _build_sustainability_sheet(ws5, green_summary, green_monthly)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_executive_summary(ws, dashboard, top_services, top_teams, opportunities,
                             total_monthly_savings, total_annual_savings,
                             generated_at, window_days, filters_json) -> None:
    ws.merge_cells("A1:F1")
    title_cell = ws.cell(row=1, column=1, value="CauSium — Relatório FinOps Executivo")
    title_cell.font = _TITLE_FONT
    title_cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30

    ws.cell(row=3, column=1, value="Gerado em:").font = _KPI_LABEL_FONT
    ws.cell(row=3, column=2, value=generated_at.strftime("%d/%m/%Y %H:%M UTC"))
    ws.cell(row=4, column=1, value="Período:").font = _KPI_LABEL_FONT
    ws.cell(row=4, column=2, value=f"{window_days} dias")
    if filters_json != "{}":
        ws.cell(row=5, column=1, value="Filtros:").font = _KPI_LABEL_FONT
        ws.cell(row=5, column=2, value=filters_json)

    # KPI section
    row = 7
    ws.cell(row=row, column=1, value="Indicadores Principais").font = _SUBTITLE_FONT
    row += 1

    kpis = [
        ("Gasto Atual", dashboard.current_month_cost, _BRL_FORMAT),
        ("Gasto Anterior", dashboard.previous_month_cost, _BRL_FORMAT),
        ("Variação MoM", dashboard.mom_change_pct / 100.0, _PCT_FORMAT),
        ("Economia Potencial (Mensal)", total_monthly_savings, _BRL_FORMAT),
        ("Economia Potencial (Anual)", total_annual_savings, _BRL_FORMAT),
        ("Contas Cloud Ativas", dashboard.active_accounts, None),
        ("Oportunidades Abertas", len(opportunities), None),
        ("Eventos (7 dias)", dashboard.event_count_7d, None),
    ]
    for label, value, fmt in kpis:
        ws.cell(row=row, column=1, value=label).font = _KPI_LABEL_FONT
        val_cell = ws.cell(row=row, column=2, value=value)
        val_cell.font = _KPI_VALUE_FONT
        if fmt:
            val_cell.number_format = fmt
        row += 1

    # Top 5 Services
    row += 1
    ws.cell(row=row, column=1, value="Top Serviços por Gasto").font = _SUBTITLE_FONT
    row += 1
    _write_table_header(ws, row, ["Serviço", "Gasto (R$)", "% do Total"])
    header_row = row
    row += 1
    for svc in top_services[:5]:
        ws.cell(row=row, column=1, value=svc.service)
        ws.cell(row=row, column=2, value=round(svc.cost_usd, 2))
        ws.cell(row=row, column=3, value=round(svc.percentage / 100.0, 3))
        row += 1
    _apply_table_style(ws, header_row + 1, row - 1, 3, currency_cols=[2], pct_cols=[3])

    # Top 5 Teams
    row += 1
    ws.cell(row=row, column=1, value="Top Equipes por Gasto").font = _SUBTITLE_FONT
    row += 1
    _write_table_header(ws, row, ["Equipe", "Gasto (R$)", "% do Total"])
    header_row = row
    row += 1
    for team in top_teams[:5]:
        ws.cell(row=row, column=1, value=team.service)
        ws.cell(row=row, column=2, value=round(team.cost_usd, 2))
        ws.cell(row=row, column=3, value=round(team.percentage / 100.0, 3))
        row += 1
    _apply_table_style(ws, header_row + 1, row - 1, 3, currency_cols=[2], pct_cols=[3])

    ws.freeze_panes = "A7"
    _auto_width(ws)


def _build_costs_sheet(ws, top_services, top_teams, trend) -> None:
    # --- Daily Spend Trend ---
    ws.cell(row=1, column=1, value="Tendência Diária de Gastos").font = _SUBTITLE_FONT
    _write_table_header(ws, 2, ["Data", "Custo Diário (R$)", "Provedor"])
    row = 3
    for t in trend:
        ws.cell(row=row, column=1, value=t.date).number_format = _DATE_FORMAT
        ws.cell(row=row, column=2, value=round(t.cost_usd, 2))
        ws.cell(row=row, column=3, value=t.provider or "Todos")
        row += 1
    trend_end = row - 1
    _apply_table_style(ws, 3, trend_end, 3, currency_cols=[2])

    # Trend line chart
    if len(trend) > 1:
        chart = LineChart()
        chart.title = "Gasto Diário (R$)"
        chart.style = 10
        chart.y_axis.title = "R$"
        chart.x_axis.title = "Data"
        chart.width = 20
        chart.height = 10
        data_ref = Reference(ws, min_col=2, min_row=2, max_row=trend_end)
        cats_ref = Reference(ws, min_col=1, min_row=3, max_row=trend_end)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        chart.legend = None
        ws.add_chart(chart, "E2")

    # --- Top Services ---
    svc_start = trend_end + 3
    ws.cell(row=svc_start, column=1, value="Gastos por Serviço").font = _SUBTITLE_FONT
    _write_table_header(ws, svc_start + 1, ["Serviço", "Gasto Mensal (R$)", "% do Total"])
    row = svc_start + 2
    for svc in top_services:
        ws.cell(row=row, column=1, value=svc.service)
        ws.cell(row=row, column=2, value=round(svc.cost_usd, 2))
        ws.cell(row=row, column=3, value=round(svc.percentage / 100.0, 3))
        row += 1
    svc_end = row - 1
    _apply_table_style(ws, svc_start + 2, svc_end, 3, currency_cols=[2], pct_cols=[3])

    # Services bar chart
    if top_services:
        chart2 = BarChart()
        chart2.type = "bar"
        chart2.title = "Top Serviços (R$)"
        chart2.style = 10
        chart2.width = 16
        chart2.height = 10
        data_ref = Reference(ws, min_col=2, min_row=svc_start + 1, max_row=svc_end)
        cats_ref = Reference(ws, min_col=1, min_row=svc_start + 2, max_row=svc_end)
        chart2.add_data(data_ref, titles_from_data=True)
        chart2.set_categories(cats_ref)
        chart2.legend = None
        ws.add_chart(chart2, f"E{svc_start}")

    # --- Top Teams ---
    team_start = svc_end + 3
    ws.cell(row=team_start, column=1, value="Gastos por Equipe").font = _SUBTITLE_FONT
    _write_table_header(ws, team_start + 1, ["Equipe", "Gasto Mensal (R$)", "% do Total"])
    row = team_start + 2
    for team in top_teams:
        ws.cell(row=row, column=1, value=team.service)
        ws.cell(row=row, column=2, value=round(team.cost_usd, 2))
        ws.cell(row=row, column=3, value=round(team.percentage / 100.0, 3))
        row += 1
    _apply_table_style(ws, team_start + 2, row - 1, 3, currency_cols=[2], pct_cols=[3])

    ws.freeze_panes = "A3"
    _auto_width(ws)


def _build_opportunities_sheet(ws, opportunities, total_monthly_savings, total_annual_savings) -> None:
    ws.cell(row=1, column=1, value="Oportunidades de Economia").font = _SUBTITLE_FONT

    # Summary row
    ws.cell(row=2, column=1, value="Economia Mensal Total:").font = _KPI_LABEL_FONT
    c = ws.cell(row=2, column=2, value=total_monthly_savings)
    c.font = _KPI_VALUE_FONT
    c.number_format = _BRL_FORMAT
    ws.cell(row=2, column=3, value="Economia Anual Total:").font = _KPI_LABEL_FONT
    c = ws.cell(row=2, column=4, value=total_annual_savings)
    c.font = _KPI_VALUE_FONT
    c.number_format = _BRL_FORMAT

    headers = [
        "Oportunidade", "Categoria", "Economia Mensal (R$)", "Economia Anual (R$)",
        "Risco", "Esforço", "Serviço Cloud", "Recurso", "Região", "Status",
    ]
    _write_table_header(ws, 4, headers)
    row = 5
    _RISK_FILLS = {
        "low": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        "medium": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        "high": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
    }
    for op in opportunities:
        ws.cell(row=row, column=1, value=op.title)
        ws.cell(row=row, column=2, value=_format_category(op.category.value))
        ws.cell(row=row, column=3, value=round(op.estimated_monthly_savings_usd, 2))
        ws.cell(row=row, column=4, value=round(op.estimated_annual_savings_usd, 2))
        risk_cell = ws.cell(row=row, column=5, value=op.risk_level.value.capitalize())
        risk_fill = _RISK_FILLS.get(op.risk_level.value)
        if risk_fill:
            risk_cell.fill = risk_fill
        ws.cell(row=row, column=6, value=op.effort_level.value.capitalize())
        ws.cell(row=row, column=7, value=op.service or "—")
        ws.cell(row=row, column=8, value=op.resource_name or "—")
        ws.cell(row=row, column=9, value=op.region or "—")
        ws.cell(row=row, column=10, value=_format_status(op.status.value))
        row += 1

    if opportunities:
        _apply_table_style(ws, 5, row - 1, 10, currency_cols=[3, 4])

    # Category pie chart
    category_counts = Counter(_format_category(op.category.value) for op in opportunities)
    if category_counts:
        pie_start = row + 2
        ws.cell(row=pie_start, column=1, value="Categoria").font = _HEADER_FONT
        ws.cell(row=pie_start, column=1).fill = _HEADER_FILL
        ws.cell(row=pie_start, column=2, value="Quantidade").font = _HEADER_FONT
        ws.cell(row=pie_start, column=2).fill = _HEADER_FILL
        r = pie_start + 1
        for cat, cnt in category_counts.most_common():
            ws.cell(row=r, column=1, value=cat)
            ws.cell(row=r, column=2, value=cnt)
            r += 1

        pie = PieChart()
        pie.title = "Oportunidades por Categoria"
        pie.width = 14
        pie.height = 10
        data_ref = Reference(ws, min_col=2, min_row=pie_start, max_row=r - 1)
        cats_ref = Reference(ws, min_col=1, min_row=pie_start + 1, max_row=r - 1)
        pie.add_data(data_ref, titles_from_data=True)
        pie.set_categories(cats_ref)
        ws.add_chart(pie, f"E{pie_start}")

    ws.freeze_panes = "A5"
    _auto_width(ws)


def _build_governance_sheet(ws, gov_summary, gov_unowned, gov_compliance) -> None:
    ws.cell(row=1, column=1, value="Governança Cloud").font = _SUBTITLE_FONT

    # Summary KPIs
    row = 3
    kpis = [
        ("Total de Recursos", gov_summary.total_resources),
        ("Recursos sem Dono", gov_summary.unowned_resources),
        ("% sem Dono", gov_summary.unowned_pct / 100.0),
        ("Custo sem Dono (R$)", gov_summary.unowned_cost_usd),
        ("Equipes Avaliadas", gov_summary.teams_evaluated),
        ("Compliance Médio (%)", gov_summary.avg_compliance_pct / 100.0),
    ]
    for label, value in kpis:
        ws.cell(row=row, column=1, value=label).font = _KPI_LABEL_FONT
        c = ws.cell(row=row, column=2, value=value)
        c.font = _KPI_VALUE_FONT
        if "R$" in label:
            c.number_format = _BRL_FORMAT
        elif "%" in label:
            c.number_format = _PCT_FORMAT
        row += 1

    # Unowned costs table
    row += 1
    ws.cell(row=row, column=1, value="Recursos sem Proprietário").font = _SUBTITLE_FONT
    row += 1
    if gov_unowned:
        headers = ["Serviço", "Recurso", "Região", "Ambiente", "Custo (R$)", "Dias Ativo"]
        _write_table_header(ws, row, headers)
        header_row = row
        row += 1
        for item in gov_unowned:
            ws.cell(row=row, column=1, value=item.service)
            ws.cell(row=row, column=2, value=item.resource_id)
            ws.cell(row=row, column=3, value=item.region)
            ws.cell(row=row, column=4, value=item.environment)
            ws.cell(row=row, column=5, value=item.cost_usd)
            ws.cell(row=row, column=6, value=item.days_active)
            row += 1
        _apply_table_style(ws, header_row + 1, row - 1, 6, currency_cols=[5])
    else:
        ws.cell(row=row, column=1, value="Nenhum recurso sem proprietário encontrado.")
        row += 1

    # Label compliance table
    row += 1
    ws.cell(row=row, column=1, value="Compliance de Tags por Equipe").font = _SUBTITLE_FONT
    row += 1
    if gov_compliance:
        headers = ["Equipe", "Custo Total (R$)", "Custo sem Tag (R$)", "Compliance (%)"]
        _write_table_header(ws, row, headers)
        header_row = row
        row += 1
        for item in gov_compliance:
            ws.cell(row=row, column=1, value=item.team)
            ws.cell(row=row, column=2, value=item.total_cost_usd)
            ws.cell(row=row, column=3, value=item.untagged_cost_usd)
            ws.cell(row=row, column=4, value=item.compliance_pct / 100.0)
            row += 1
        _apply_table_style(ws, header_row + 1, row - 1, 4, currency_cols=[2, 3], pct_cols=[4])
    else:
        ws.cell(row=row, column=1, value="Dados de compliance não disponíveis.")

    ws.freeze_panes = "A3"
    _auto_width(ws)


def _build_sustainability_sheet(ws, green_summary, green_monthly) -> None:
    ws.cell(row=1, column=1, value="Sustentabilidade — Emissões de Carbono").font = _SUBTITLE_FONT

    # Summary KPIs
    row = 3
    kpis = [
        ("Emissões Totais (kgCO₂e)", green_summary.total_kg_co2e, "#,##0.0"),
        ("Custo Associado (R$)", green_summary.total_cost_usd, _BRL_FORMAT),
        ("Intensidade Média (gCO₂e/R$)", green_summary.intensity_avg, "#,##0.0"),
        ("Variação MoM", (green_summary.mom_delta_pct or 0) / 100.0, _PCT_FORMAT),
        ("Meses Disponíveis", green_summary.months_available, None),
        ("Fonte dos Dados", green_summary.data_source, None),
    ]
    for label, value, fmt in kpis:
        ws.cell(row=row, column=1, value=label).font = _KPI_LABEL_FONT
        c = ws.cell(row=row, column=2, value=value)
        c.font = _KPI_VALUE_FONT
        if fmt:
            c.number_format = fmt
        row += 1

    # Note
    row += 1
    ws.cell(row=row, column=1, value=green_summary.note).font = Font(
        name="Calibri", italic=True, color="666666", size=9
    )

    # Monthly emissions table
    row += 2
    ws.cell(row=row, column=1, value="Emissões Mensais").font = _SUBTITLE_FONT
    row += 1
    if green_monthly:
        headers = ["Mês", "Emissões (kgCO₂e)", "Custo (R$)", "Variação (%)"]
        _write_table_header(ws, row, headers)
        header_row = row
        row += 1
        for m in green_monthly:
            ws.cell(row=row, column=1, value=m.month)
            ws.cell(row=row, column=2, value=m.kg_co2e)
            ws.cell(row=row, column=3, value=m.cost_usd)
            ws.cell(row=row, column=4, value=(m.delta_pct or 0) / 100.0 if m.delta_pct else None)
            row += 1
        _apply_table_style(ws, header_row + 1, row - 1, 4, currency_cols=[3], pct_cols=[4])

        # Emissions line chart
        if len(green_monthly) > 1:
            chart = LineChart()
            chart.title = "Emissões Mensais (kgCO₂e)"
            chart.style = 10
            chart.y_axis.title = "kgCO₂e"
            chart.width = 18
            chart.height = 10
            data_ref = Reference(ws, min_col=2, min_row=header_row, max_row=row - 1)
            cats_ref = Reference(ws, min_col=1, min_row=header_row + 1, max_row=row - 1)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats_ref)
            chart.legend = None
            ws.add_chart(chart, f"F{header_row}")
    else:
        ws.cell(row=row, column=1, value="Dados de emissões não disponíveis para este período.")

    ws.freeze_panes = "A3"
    _auto_width(ws)