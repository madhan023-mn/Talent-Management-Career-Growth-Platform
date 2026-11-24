"""
Enterprise Employee Career & Performance PDF Report Generator
Talent Management & Career Growth Platform

Redesigned corporate layout matching executive HR reference specifications:
1. Report Header (Talent Growth Technologies, Confidential, Period, Date)
2. Employee Information (Compact 2-column key-value table)
3. Career Readiness Overview (4 KPI Metric Cards)
4. Skills Gap Analysis (Compact table with matched/unmatched indicators)
5. Key Development Actions (3-5 specific, gap-driven recommendations)
6. Career Development Plan (Phases: 0-3m, 3-6m, 6-12m)
7. Review Status (Performance score, Active/Completed goals, Training status)
8. Acknowledgement (Employee, Manager, HR signatures and dates)
"""

from __future__ import annotations
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image, PageBreak
)

THEME_PALETTES = {
    "Navy & Teal": {
        "primary": "#0F172A",
        "accent": "#1E40AF",
        "sub_accent": "#0D9488",
        "card_bg": "#F8FAFC",
        "border": "#CBD5E1",
        "header_bg": "#F1F5F9"
    },
    "Modern Indigo": {
        "primary": "#1E1B4B",
        "accent": "#4338CA",
        "sub_accent": "#2563EB",
        "card_bg": "#F5F3FF",
        "border": "#C7D2FE",
        "header_bg": "#EDE9FE"
    },
    "Emerald Executive": {
        "primary": "#064E3B",
        "accent": "#047857",
        "sub_accent": "#059669",
        "card_bg": "#ECFDF5",
        "border": "#A7F3D0",
        "header_bg": "#D1FAE5"
    },
    "Classic Slate": {
        "primary": "#1E293B",
        "accent": "#334155",
        "sub_accent": "#475569",
        "card_bg": "#F8FAFC",
        "border": "#CBD5E1",
        "header_bg": "#F1F5F9"
    }
}


def _escape_xml(text: Any) -> str:
    """Safely escapes XML entities for ReportLab Paragraph rendering."""
    if text is None:
        return ""
    s = str(text)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_numbered_canvas(company_name: str, employee_name: str):
    """
    Two-pass canvas that computes total page count dynamically
    and draws professional running headers and footers with Page X of Y.
    """
    clean_company = company_name.strip() if company_name else "TALENT GROWTH TECHNOLOGIES"
    if "INNOTIQ" in clean_company.upper():
        clean_company = "TALENT GROWTH TECHNOLOGIES"

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_page_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica-Bold", 7)
            self.setFillColor(colors.HexColor("#64748B"))

            # Running Header on page 2+
            if self._pageNumber > 1:
                self.setStrokeColor(colors.HexColor("#E2E8F0"))
                self.setLineWidth(0.5)
                self.line(36, A4[1] - 22, A4[0] - 36, A4[1] - 22)
                hdr_left = f"{clean_company.upper()} · EMPLOYEE CAREER & PERFORMANCE REPORT"
                self.drawString(36, A4[1] - 17, hdr_left)
                self.setFont("Helvetica", 7)
                self.drawRightString(A4[0] - 36, A4[1] - 17, employee_name)

            # Running Footer on all pages
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 24, A4[0] - 36, 24)

            self.setFont("Helvetica-Bold", 6.8)
            footer_left = f"{clean_company.upper()} | CONFIDENTIAL – HUMAN RESOURCES"
            page_str = f"Page {self._pageNumber} of {page_count}"
            self.drawString(36, 14, footer_left)
            self.setFont("Helvetica", 6.8)
            self.drawRightString(A4[0] - 36, 14, page_str)
            self.restoreState()

    return NumberedCanvas


def create_report(
    profile: Dict[str, Any],
    skills: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    assessments: Optional[List[Dict[str, Any]]] = None,
    progress: Optional[List[Dict[str, Any]]] = None,
    goals: Optional[List[Dict[str, Any]]] = None,
    reviews: Optional[List[Dict[str, Any]]] = None,
    trainings: Optional[List[Dict[str, Any]]] = None,
    pdf_config: Optional[Dict[str, Any]] = None,
    org_id: Optional[str] = None
) -> bytes:
    """
    Renders an executive, publication-grade 2-page corporate talent report:
      PAGE 1:
        1. Report Header (Talent Growth Technologies, Confidential, Period, Date)
        2. Employee Information (Compact 2-column table)
        3. Career Readiness Overview (4 KPI Cards)
        4. Skills Gap Analysis (Compact table with matched/unmatched indicators)
        5. Key Development Actions (Top 3-5 specific recommendations)
      PAGE 2:
        6. Career Development Plan (Phases 0-3m, 3-6m, 6-12m)
        7. Review Status (Performance Score, Active/Completed Goals, Training Status)
        8. Acknowledgement (Employee, Manager, and HR Signatures & Dates)
    """
    # --------------------------------------------------------------------------
    # 0. RESOLVE BRANDING & CONFIGURATION
    # --------------------------------------------------------------------------
    if not pdf_config and org_id:
        try:
            from services.settings import get_org_pdf_config
            pdf_config = get_org_pdf_config(org_id)
        except Exception:
            pdf_config = {}

    cfg = pdf_config or {}
    raw_company = (
        cfg.get("company_name")
        or profile.get("company")
        or "TALENT GROWTH TECHNOLOGIES"
    ).strip()
    if not raw_company or "INNOTIQ" in raw_company.upper():
        company_name = "TALENT GROWTH TECHNOLOGIES"
    else:
        company_name = raw_company

    theme_name = cfg.get("theme_color", "Navy & Teal")
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Navy & Teal"])

    primary_hex = palette["primary"]
    accent_hex = palette["accent"]
    sub_accent_hex = palette["sub_accent"]
    card_bg_hex = palette.get("card_bg", "#F8FAFC")
    border_hex = palette.get("border", "#CBD5E1")
    header_bg_hex = palette.get("header_bg", "#F1F5F9")

    # Resolve Employee Fields
    user_name = (profile.get("name") or "Employee").strip()
    emp_id = (
        profile.get("employee_id")
        or profile.get("emp_id")
        or (f"EMP{profile.get('user_id', 1):03d}" if profile.get("user_id") else "Not recorded")
    )
    current_role = profile.get("job_title") or profile.get("designation") or "Not recorded"
    dept = profile.get("department") or "Not recorded"
    years_val = profile.get("years_experience")
    years_str = f"{float(years_val):g} Years" if (years_val is not None and float(years_val) > 0) else "Not recorded"

    target_role = profile.get("target_role") or "Not selected"
    if target_role in ["-- Choose Target Role --", "-- Choose Benchmark Role --", "-- Select Target Role --"]:
        target_role = "Not selected"

    target_level = profile.get("target_level") or "Not specified"
    if target_level in ["-- Choose Target Level --", "-- Select Target Level --"]:
        target_level = "Not specified"

    # Automatically load database records if not provided
    if (reviews is None or len(reviews) == 0) and emp_id != "Not recorded":
        try:
            from services.core import get_performance_reviews
            reviews = get_performance_reviews(employee_id=emp_id, org_id=org_id)
        except Exception:
            reviews = []

    if (goals is None or len(goals) == 0) and emp_id != "Not recorded":
        try:
            from services.core import get_goals
            goals = get_goals(employee_id=emp_id, org_id=org_id)
        except Exception:
            goals = []

    if (trainings is None or len(trainings) == 0) and emp_id != "Not recorded":
        try:
            from services.core import get_training_records
            trainings = get_training_records(employee_id=emp_id, org_id=org_id)
        except Exception:
            trainings = []

    # Reporting Period & Date
    report_period = "2025–2026 Annual Review"
    if reviews and len(reviews) > 0:
        first_rev = reviews[0]
        if first_rev.get("review_period"):
            report_period = str(first_rev["review_period"])

    now = datetime.now()
    date_format = cfg.get("date_format") or "%B %d, %Y"
    try:
        generated_date = now.strftime(date_format)
    except Exception:
        generated_date = now.strftime("%B %d, %Y")

    # Document Template Setup on A4
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=26,
        bottomMargin=26
    )

    styles = getSampleStyleSheet()

    # Typography Styles
    org_title_style = ParagraphStyle(
        'OrgHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=12.5,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=1
    )
    confidential_badge_style = ParagraphStyle(
        'ConfidentialBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#DC2626'),
        alignment=2  # Right-aligned
    )
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13.5,
        leading=15.5,
        textColor=colors.HexColor(primary_hex),
        spaceAfter=2
    )
    meta_sub_style = ParagraphStyle(
        'MetaSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=colors.HexColor('#64748B')
    )
    section_h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor(primary_hex),
        spaceBefore=3,
        spaceAfter=2.5
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.2,
        textColor=colors.HexColor('#475569')
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.2,
        textColor=colors.HexColor('#0F172A')
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor('#1E293B')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor(primary_hex)
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor('#0F172A')
    )
    not_recorded_style = ParagraphStyle(
        'NotRecorded',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor('#64748B')
    )

    # KPI Card Styles
    kpi_title_style = ParagraphStyle(
        'KpiTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor('#475569'),
        spaceAfter=1.5
    )
    kpi_metric_style = ParagraphStyle(
        'KpiMetric',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=1
    )
    kpi_metric_green = ParagraphStyle(
        'KpiMetricGreen',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#059669'),
        spaceAfter=1
    )
    kpi_sub_style = ParagraphStyle(
        'KpiSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6,
        leading=7.8,
        textColor=colors.HexColor('#64748B')
    )

    elements: List[Any] = []

    # ==========================================================================
    # PAGE 1: EVALUATION & COMPETENCY DIAGNOSIS
    # ==========================================================================

    # --------------------------------------------------------------------------
    # 1. REPORT HEADER
    # --------------------------------------------------------------------------
    logo_img = None
    logo_base64 = cfg.get("logo_base64")
    if logo_base64 and "," in logo_base64:
        try:
            raw_b64 = logo_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            img_buf = BytesIO(img_bytes)
            logo_img = Image(img_buf, width=85, height=24)
        except Exception:
            logo_img = None

    hdr_left_flowables = [
        Paragraph(f"<b>{_escape_xml(company_name.upper())}</b>", org_title_style),
        Paragraph("EMPLOYEE CAREER &amp; PERFORMANCE REPORT", doc_title_style),
        Paragraph(f"<b>Reporting Period:</b> {_escape_xml(report_period)} &nbsp;|&nbsp; <b>Generated:</b> {_escape_xml(generated_date)}", meta_sub_style)
    ]
    hdr_right_flowables = [
        Paragraph("CONFIDENTIAL – HUMAN RESOURCES", confidential_badge_style)
    ]
    if logo_img:
        hdr_right_flowables.append(Spacer(1, 2))
        hdr_right_flowables.append(logo_img)

    header_table = Table([[hdr_left_flowables, hdr_right_flowables]], colWidths=[360, 163])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(accent_hex), spaceAfter=3, spaceBefore=2))

    # --------------------------------------------------------------------------
    # 2. EMPLOYEE INFORMATION (Compact 2-Column Table)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("EMPLOYEE INFORMATION", section_h1_style))
    emp_info_data = [
        [
            Paragraph("<b>Employee:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(user_name)}</b>", meta_val_style),
            Paragraph("<b>Employee ID:</b>", meta_label_style),
            Paragraph(_escape_xml(emp_id), meta_val_style)
        ],
        [
            Paragraph("<b>Department:</b>", meta_label_style),
            Paragraph(_escape_xml(dept), meta_val_style),
            Paragraph("<b>Designation:</b>", meta_label_style),
            Paragraph(_escape_xml(current_role), meta_val_style)
        ],
        [
            Paragraph("<b>Experience:</b>", meta_label_style),
            Paragraph(_escape_xml(years_str), meta_val_style),
            Paragraph("<b>Target Level:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(target_level)}</b> (Target: {_escape_xml(target_role)})", meta_val_style)
        ]
    ]
    emp_table = Table(emp_info_data, colWidths=[95, 166, 95, 167])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 3))

    # --------------------------------------------------------------------------
    # 3. CAREER READINESS OVERVIEW (4 KPI Metrics)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("CAREER READINESS OVERVIEW", section_h1_style))

    # Metric 1: Role Readiness (%)
    match_score = int(analysis.get("match") or 0)
    card_readiness = [
        Paragraph("Role Readiness", kpi_title_style),
        Paragraph(f"{match_score}%", kpi_metric_style),
        Paragraph(f"Target: {_escape_xml(target_role)}", kpi_sub_style)
    ]

    # Metric 2: Verified Skills
    skills_count = len(skills)
    card_skills = [
        Paragraph("Verified Skills", kpi_title_style),
        Paragraph(f"{skills_count}", kpi_metric_style),
        Paragraph("Validated Competencies", kpi_sub_style)
    ]

    # Metric 3: Target Skills Matched
    if gaps:
        matched_count = sum(1 for g in gaps if g.get("gap", 0) == 0)
        total_bench = len(gaps)
        match_metric = f"{matched_count} of {total_bench}"
        match_sub = f"{total_bench - matched_count} Gap Identified" if (total_bench - matched_count) > 0 else "All Benchmarks Met"
    elif target_role and target_role != "Not selected":
        match_metric = "All Matched"
        match_sub = "Zero Gaps Identified"
    else:
        match_metric = "Pending"
        match_sub = "Select Benchmark Role"

    card_matches = [
        Paragraph("Target Skills Matched", kpi_title_style),
        Paragraph(match_metric, kpi_metric_style),
        Paragraph(match_sub, kpi_sub_style)
    ]

    # Metric 4: Performance Review Status
    if reviews and len(reviews) > 0:
        latest_rev = reviews[0]
        latest_score = float(latest_rev.get("performance_score") or 0.0)
        perf_metric = f"{latest_score:.1f} / 5.0"
        perf_sub = "Evaluation Recorded"
    else:
        perf_metric = "Not recorded"
        perf_sub = "No reviews on file"

    card_perf = [
        Paragraph("Performance Review Status", kpi_title_style),
        Paragraph(perf_metric, kpi_metric_green if (reviews and len(reviews) > 0) else kpi_title_style),
        Paragraph(perf_sub, kpi_sub_style)
    ]

    kpi_data = [[card_readiness, '', card_skills, '', card_matches, '', card_perf]]
    kpi_table = Table(kpi_data, colWidths=[124, 9, 124, 9, 124, 9, 124])
    kpi_t_style = [('VALIGN', (0,0), (-1,-1), 'TOP')]
    for col_i in [0, 2, 4, 6]:
        kpi_t_style.extend([
            ('BACKGROUND', (col_i, 0), (col_i, 0), colors.HexColor(card_bg_hex)),
            ('BOX', (col_i, 0), (col_i, 0), 0.5, colors.HexColor(border_hex)),
            ('TOPPADDING', (col_i, 0), (col_i, 0), 3.5),
            ('BOTTOMPADDING', (col_i, 0), (col_i, 0), 3.5),
            ('LEFTPADDING', (col_i, 0), (col_i, 0), 5),
            ('RIGHTPADDING', (col_i, 0), (col_i, 0), 5),
        ])
    for gap_i in [1, 3, 5]:
        kpi_t_style.extend([
            ('TOPPADDING', (gap_i, 0), (gap_i, 0), 0),
            ('BOTTOMPADDING', (gap_i, 0), (gap_i, 0), 0),
            ('LEFTPADDING', (gap_i, 0), (gap_i, 0), 0),
            ('RIGHTPADDING', (gap_i, 0), (gap_i, 0), 0),
        ])
    kpi_table.setStyle(TableStyle(kpi_t_style))
    elements.append(kpi_table)
    elements.append(Spacer(1, 3))

    # --------------------------------------------------------------------------
    # 4. SKILLS GAP ANALYSIS (Compact Table with Matched Indicators)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("SKILLS GAP ANALYSIS", section_h1_style))
    if gaps:
        gap_rows = [[
            Paragraph("<b>Skill</b>", table_header_style),
            Paragraph("<b>Current Level</b>", table_header_style),
            Paragraph("<b>Required Level</b>", table_header_style),
            Paragraph("<b>Status / Gap</b>", table_header_style),
            Paragraph("<b>Priority</b>", table_header_style)
        ]]
        for g in gaps:
            pri = str(g.get("priority", "Medium"))
            pri_color = "#DC2626" if pri == "High" else ("#D97706" if pri == "Medium" else "#059669")
            gap_val = int(g.get("gap", 0))

            if gap_val == 0:
                gap_text = "<font color='#059669'><b>Matched [✓]</b></font>"
            else:
                gap_text = f"<font color='#DC2626'><b>Gap: -{gap_val} Level{'s' if gap_val > 1 else ''}</b></font>"

            cur_lvl = g.get("current", 0)
            req_lvl = g.get("required", 0)

            gap_rows.append([
                Paragraph(_escape_xml(g.get("skill", "Competency")), body_style),
                Paragraph(f"Level {cur_lvl}", body_style),
                Paragraph(f"Level {req_lvl}", body_style),
                Paragraph(gap_text, body_style),
                Paragraph(f"<font color='{pri_color}'><b>{_escape_xml(pri)}</b></font>", body_style)
            ])
        gap_table = Table(gap_rows, colWidths=[153, 90, 90, 100, 90])
        gap_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(header_bg_hex)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]
        for r_idx in range(1, len(gap_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            gap_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        gap_table.setStyle(TableStyle(gap_style))
        elements.append(gap_table)
    else:
        if not target_role or target_role == "Not selected":
            elements.append(Paragraph("Target role not selected. Please select a benchmark role in the platform to generate competency gap telemetry.", not_recorded_style))
        else:
            elements.append(Paragraph(f"All evaluated competencies for <b>{_escape_xml(target_role)}</b> meet or exceed required benchmark levels.", body_style))
    elements.append(Spacer(1, 3))

    # --------------------------------------------------------------------------
    # 5. KEY DEVELOPMENT ACTIONS (Top 3–5 Recommendations)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("KEY DEVELOPMENT ACTIONS", section_h1_style))
    active_gaps = [g for g in gaps if g.get("gap", 0) > 0] if gaps else []
    if active_gaps:
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        sorted_gaps = sorted(active_gaps, key=lambda x: priority_order.get(x.get("priority", "Medium"), 4))[:4]

        action_rows = [[
            Paragraph("<b>Priority Area</b>", table_header_style),
            Paragraph("<b>Target Growth</b>", table_header_style),
            Paragraph("<b>Actionable Recommendation</b>", table_header_style)
        ]]
        for g in sorted_gaps:
            sk_name = _escape_xml(g.get("skill", "Competency"))
            pri_tag = _escape_xml(g.get("priority", "Medium"))
            pri_color = "#DC2626" if pri_tag == "High" else ("#D97706" if pri_tag == "Medium" else "#059669")
            cur_l = g.get("current", 0)
            req_l = g.get("required", 0)

            rec_text = f"Advance competency from Level {cur_l} to Level {req_l} through practical hands-on project delivery, architectural code reviews, and structured certification."

            action_rows.append([
                Paragraph(f"<b>{sk_name}</b> &nbsp;<font color='{pri_color}'><b>[{pri_tag}]</b></font>", body_style),
                Paragraph(f"Level {cur_l} &rarr; Level {req_l}", body_style),
                Paragraph(rec_text, body_style)
            ])
        action_table = Table(action_rows, colWidths=[143, 90, 290])
        action_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor(header_bg_hex)),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]
        for r_idx in range(1, len(action_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            action_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        action_table.setStyle(TableStyle(action_style))
        elements.append(action_table)
    else:
        elements.append(Paragraph("No active skill gap development actions required. Employee meets all benchmark requirements for current career track.", not_recorded_style))

    # ==========================================================================
    # PAGE BREAK: PROCEED TO PAGE 2 (ROADMAP, GOVERNANCE & ACKNOWLEDGEMENT)
    # ==========================================================================
    elements.append(PageBreak())

    # ==========================================================================
    # PAGE 2: ROADMAP, GOVERNANCE & SIGN-OFF
    # ==========================================================================

    # --------------------------------------------------------------------------
    # 6. CAREER DEVELOPMENT PLAN (Phases 0-3m, 3-6m, 6-12m)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("CAREER DEVELOPMENT PLAN", section_h1_style))
    plan_rows = [
        [
            Paragraph("<b>Timeline</b>", table_header_style),
            Paragraph("<b>Development Focus</b>", table_header_style),
            Paragraph("<b>Expected Outcome</b>", table_header_style)
        ],
        [
            Paragraph("<b>0–3 months</b><br/>Foundation", body_style),
            Paragraph("<b>Core Competency Alignment</b><br/>Address foundational skill gaps and complete core benchmark certifications.", body_style),
            Paragraph(f"Establish technical readiness in critical areas required for {target_role}.", body_style)
        ],
        [
            Paragraph("<b>3–6 months</b><br/>Execution", body_style),
            Paragraph("<b>Cross-Functional Project Ownership</b><br/>Lead subsystem implementations, cross-team reviews, and architectural deliverables.", body_style),
            Paragraph("Demonstrate autonomous delivery and measurable operational impact across sprints.", body_style)
        ],
        [
            Paragraph("<b>6–12 months</b><br/>Readiness", body_style),
            Paragraph(f"<b>{target_role} Transition</b><br/>Undertake formal readiness review, mentor junior team members, and assume target scope.", body_style),
            Paragraph(f"Full operational transition into {target_role} responsibilities and expectations.", body_style)
        ]
    ]
    plan_table = Table(plan_rows, colWidths=[85, 219, 219])
    plan_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(header_bg_hex)),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]
    plan_table.setStyle(TableStyle(plan_style))
    elements.append(plan_table)
    elements.append(Spacer(1, 4))

    # --------------------------------------------------------------------------
    # 7. REVIEW STATUS (Performance, Goals, Training)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("REVIEW STATUS", section_h1_style))

    # Compile actual metrics
    # A. Performance
    if reviews and len(reviews) > 0:
        latest_rev = reviews[0]
        score_val = float(latest_rev.get("performance_score") or 0.0)
        perf_status_text = f"<b>Evaluation Recorded:</b> {score_val:.1f} / 5.0 ({_escape_xml(latest_rev.get('review_period') or 'Annual Review')})"
        perf_notes_text = f"<b>Feedback:</b> {_escape_xml(latest_rev.get('manager_feedback') or latest_rev.get('comments') or 'Objectives met.')}"
    else:
        perf_status_text = "No performance reviews recorded"
        perf_notes_text = "Employee has not yet completed a formal manager performance evaluation cycle."

    # B. Goals
    if goals and len(goals) > 0:
        active_goals_cnt = sum(1 for g in goals if str(g.get("status", "")).lower() in ["in progress", "not started", "pending review", "pending"])
        completed_goals_cnt = sum(1 for g in goals if str(g.get("status", "")).lower() == "completed")
        goal_status_text = f"<b>Active Goals:</b> {active_goals_cnt} &nbsp;|&nbsp; <b>Completed Goals:</b> {completed_goals_cnt}"
        recent_goal_titles = ", ".join([str(g.get("title", "")) for g in goals[:2]])
        goal_notes_text = f"<b>Key Goals:</b> {_escape_xml(recent_goal_titles)}"
    else:
        goal_status_text = "No active goals"
        goal_notes_text = "No milestones or quarterly goals recorded in employee profile."

    # C. Training
    if trainings and len(trainings) > 0:
        completed_tr_cnt = sum(1 for t in trainings if str(t.get("status", "")).lower() == "completed")
        active_tr_cnt = len(trainings) - completed_tr_cnt
        training_status_text = f"<b>Enrolled Courses:</b> {len(trainings)} &nbsp;|&nbsp; <b>Completed:</b> {completed_tr_cnt}"
        tr_titles = ", ".join([str(t.get("course_name", "")) for t in trainings[:2]])
        training_notes_text = f"<b>Curriculum:</b> {_escape_xml(tr_titles)}"
    else:
        training_status_text = "Training status: None assigned"
        training_notes_text = "No formal training programs currently assigned."

    status_data = [
        [
            Paragraph("<b>Performance Review:</b>", meta_label_style),
            Paragraph(f"{perf_status_text}<br/>{perf_notes_text}", body_style)
        ],
        [
            Paragraph("<b>Goals &amp; Objectives:</b>", meta_label_style),
            Paragraph(f"{goal_status_text}<br/>{goal_notes_text}", body_style)
        ],
        [
            Paragraph("<b>Training Status:</b>", meta_label_style),
            Paragraph(f"{training_status_text}<br/>{training_notes_text}", body_style)
        ]
    ]
    status_table = Table(status_data, colWidths=[120, 403])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 4))

    # --------------------------------------------------------------------------
    # 8. ACKNOWLEDGEMENT (Signatures & Date Fields)
    # --------------------------------------------------------------------------
    elements.append(Paragraph("ACKNOWLEDGEMENT", section_h1_style))
    signoff_rows = [
        [
            Paragraph(
                f"<b>Employee Signature</b><br/><br/><br/>"
                f"____________________________________<br/>"
                f"<b>{_escape_xml(user_name)}</b><br/>"
                f"Date: ________________________",
                body_style
            ),
            "",
            Paragraph(
                f"<b>Reviewing Manager Signature</b><br/><br/><br/>"
                f"____________________________________<br/>"
                f"<b>Authorized Evaluator</b><br/>"
                f"Date: ________________________",
                body_style
            ),
            "",
            Paragraph(
                f"<b>HR Governance Signature</b><br/><br/><br/>"
                f"____________________________________<br/>"
                f"<b>Talent Committee Director</b><br/>"
                f"Date: ________________________",
                body_style
            )
        ]
    ]
    signoff_table = Table(signoff_rows, colWidths=[169, 8, 169, 8, 169])
    signoff_style = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for c_i in [0, 2, 4]:
        signoff_style.extend([
            ('BACKGROUND', (c_i, 0), (c_i, 0), colors.HexColor(card_bg_hex)),
            ('BOX', (c_i, 0), (c_i, 0), 0.5, colors.HexColor(border_hex)),
            ('TOPPADDING', (c_i, 0), (c_i, 0), 4),
            ('BOTTOMPADDING', (c_i, 0), (c_i, 0), 4),
            ('LEFTPADDING', (c_i, 0), (c_i, 0), 5),
            ('RIGHTPADDING', (c_i, 0), (c_i, 0), 5),
        ])
    for g_i in [1, 3]:
        signoff_style.extend([
            ('TOPPADDING', (g_i, 0), (g_i, 0), 0),
            ('BOTTOMPADDING', (g_i, 0), (g_i, 0), 0),
            ('LEFTPADDING', (g_i, 0), (g_i, 0), 0),
            ('RIGHTPADDING', (g_i, 0), (g_i, 0), 0),
        ])
    signoff_table.setStyle(TableStyle(signoff_style))
    elements.append(KeepTogether(signoff_table))

    # Confidentiality Note
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=2, spaceBefore=2))
    elements.append(Paragraph(
        "<b>CONFIDENTIALITY NOTICE:</b> This dossier contains official workforce intelligence, competency evaluation scores, "
        "and career development roadmaps. It is intended strictly for authorized organizational human resources governance and the named employee.",
        meta_sub_style
    ))

    # --------------------------------------------------------------------------
    # 9. BUILD DOCUMENT WITH TWO-PASS NUMBERED CANVAS
    # --------------------------------------------------------------------------
    doc.build(elements, canvasmaker=make_numbered_canvas(company_name, user_name))
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
