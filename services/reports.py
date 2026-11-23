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
        "accent": "#2563EB",
        "sub_accent": "#0D9488",
        "card_bg": "#F8FAFC",
        "border": "#CBD5E1"
    },
    "Modern Indigo": {
        "primary": "#1E1B4B",
        "accent": "#4F46E5",
        "sub_accent": "#2563EB",
        "card_bg": "#EEF2FF",
        "border": "#C7D2FE"
    },
    "Emerald Executive": {
        "primary": "#064E3B",
        "accent": "#059669",
        "sub_accent": "#10B981",
        "card_bg": "#ECFDF5",
        "border": "#A7F3D0"
    },
    "Classic Slate": {
        "primary": "#1E293B",
        "accent": "#475569",
        "sub_accent": "#64748B",
        "card_bg": "#F8FAFC",
        "border": "#CBD5E1"
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
    clean_company = company_name.strip() if company_name else ""
    if not clean_company or "INNOTIQ" in clean_company.upper():
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
                self.line(36, A4[1] - 20, A4[0] - 36, A4[1] - 20)
                hdr_left = f"{clean_company} · EMPLOYEE CAREER & PERFORMANCE REPORT"
                self.drawString(36, A4[1] - 16, hdr_left.upper())
                self.setFont("Helvetica", 7)
                self.drawRightString(A4[0] - 36, A4[1] - 16, employee_name)

            # Running Footer on all pages
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 24, A4[0] - 36, 24)

            self.setFont("Helvetica-Bold", 6.8)
            footer_left = f"{clean_company.upper()} | CONFIDENTIAL & PROPRIETARY"
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
      Page 1: Employee Performance & Competency
        A. Employee Information
        B. Career Readiness Overview (4 key metrics)
        C. Skills Gap Analysis
        D. Performance Summary
      Page 2: Career Development Plan
        A. Verified Competencies
        B. Development Priorities
        C. Career Growth Roadmap
        D. Goals and Achievements
        E. Review and Acknowledgement (Sign-off)
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

    # Employee Information Fields
    user_name = (profile.get("name") or "Employee").strip()
    emp_id = (
        profile.get("employee_id")
        or profile.get("emp_id")
        or (f"EMP{profile.get('user_id', 1):03d}" if profile.get("user_id") else "Not recorded")
    )
    current_role = profile.get("job_title") or profile.get("designation") or "Not recorded"
    target_role = profile.get("target_role") or "Not selected"
    if target_role in ["-- Choose Target Role --", "-- Choose Benchmark Role --", "-- Select Target Role --"]:
        target_role = "Not selected"

    dept = profile.get("department") or "Not recorded"
    years_val = profile.get("years_experience")
    years_str = f"{float(years_val):g} Years" if (years_val is not None and float(years_val) > 0) else "Not recorded"
    target_level = profile.get("target_level") or "Not specified"
    if target_level in ["-- Choose Target Level --", "-- Select Target Level --"]:
        target_level = "Not specified"

    # Reporting Period Resolution
    report_period = "2025–2026 Annual Review"
    if reviews:
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
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    # Corporate Typography & Styling
    org_title_style = ParagraphStyle(
        'OrgHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=1
    )
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.HexColor(primary_hex),
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'DossierSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=1
    )
    section_h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(primary_hex),
        spaceBefore=4,
        spaceAfter=3
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor('#475569')
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor('#1E293B')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor(primary_hex)
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor('#0F172A')
    )
    not_recorded_style = ParagraphStyle(
        'NotRecorded',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor('#64748B')
    )

    # KPI Card Styles
    kpi_title_style = ParagraphStyle(
        'KpiTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#475569'),
        spaceAfter=2
    )
    kpi_metric_style = ParagraphStyle(
        'KpiMetric',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=15,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=1
    )
    kpi_metric_green = ParagraphStyle(
        'KpiMetricGreen',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=15,
        textColor=colors.HexColor('#059669'),
        spaceAfter=1
    )
    kpi_sub_style = ParagraphStyle(
        'KpiSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.2,
        leading=8,
        textColor=colors.HexColor('#64748B')
    )

    elements: List[Any] = []

    # ==========================================================================
    # PAGE 1: EMPLOYEE PERFORMANCE & COMPETENCY
    # ==========================================================================

    # --- Header & Corporate Branding ---
    logo_img = None
    logo_base64 = cfg.get("logo_base64")
    if logo_base64 and "," in logo_base64:
        try:
            raw_b64 = logo_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            img_buf = BytesIO(img_bytes)
            logo_img = Image(img_buf, width=95, height=26)
        except Exception:
            logo_img = None

    if logo_img:
        hdr_table_data = [
            [
                [
                    Paragraph(f"<b>{_escape_xml(company_name.upper())}</b>", org_title_style),
                    Paragraph("EMPLOYEE CAREER &amp; PERFORMANCE REPORT", doc_title_style),
                    Paragraph("ENTERPRISE TALENT EVALUATION &amp; DEVELOPMENT DOSSIER", subtitle_style)
                ],
                logo_img
            ]
        ]
        hdr_table = Table(hdr_table_data, colWidths=[413, 110])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(hdr_table)
    else:
        elements.append(Paragraph(f"<b>{_escape_xml(company_name.upper())}</b>", org_title_style))
        elements.append(Paragraph("EMPLOYEE CAREER &amp; PERFORMANCE REPORT", doc_title_style))
        elements.append(Paragraph("ENTERPRISE TALENT EVALUATION &amp; DEVELOPMENT DOSSIER", subtitle_style))

    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(accent_hex), spaceAfter=4, spaceBefore=2))

    # --- 1.A: Employee Information ---
    elements.append(Paragraph("EMPLOYEE INFORMATION", section_h1_style))
    emp_info_data = [
        [
            Paragraph("<b>Employee Name:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(user_name)}</b>", meta_val_style),
            Paragraph("<b>Employee ID:</b>", meta_label_style),
            Paragraph(_escape_xml(emp_id), meta_val_style)
        ],
        [
            Paragraph("<b>Department:</b>", meta_label_style),
            Paragraph(_escape_xml(dept), meta_val_style),
            Paragraph("<b>Current Designation:</b>", meta_label_style),
            Paragraph(_escape_xml(current_role), meta_val_style)
        ],
        [
            Paragraph("<b>Years of Experience:</b>", meta_label_style),
            Paragraph(_escape_xml(years_str), meta_val_style),
            Paragraph("<b>Target Designation:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(target_role)}</b>", meta_val_style)
        ],
        [
            Paragraph("<b>Target Career Level:</b>", meta_label_style),
            Paragraph(_escape_xml(target_level), meta_val_style),
            Paragraph("<b>Reporting Period:</b>", meta_label_style),
            Paragraph(_escape_xml(report_period), meta_val_style)
        ]
    ]
    emp_table = Table(emp_info_data, colWidths=[105, 156, 105, 157])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 4))

    # --- 1.B: Career Readiness Overview (4 Key Metrics) ---
    elements.append(Paragraph("CAREER READINESS OVERVIEW", section_h1_style))

    # 1. Role Readiness Percentage
    match_score = int(analysis.get("match") or 0)
    card_readiness = [
        Paragraph("Role Readiness", kpi_title_style),
        Paragraph(f"{match_score}%", kpi_metric_style),
        Paragraph(f"Target: {_escape_xml(target_role)}", kpi_sub_style)
    ]

    # 2. Performance Rating
    if reviews:
        latest_rev = reviews[0]
        latest_score = float(latest_rev.get("performance_score") or 0.0)
        rating_metric = f"{latest_score:.1f} / 5.0"
        if latest_score >= 4.5:
            badge_text = "Top Performer"
        elif latest_score >= 4.0:
            badge_text = "Exceeds Expectations"
        elif latest_score >= 3.0:
            badge_text = "Meets Expectations"
        else:
            badge_text = "Needs Development"
        rating_sub = f"{badge_text}"
    else:
        rating_metric = "Not recorded"
        rating_sub = "No evaluations on file"

    card_perf = [
        Paragraph("Performance Rating", kpi_title_style),
        Paragraph(rating_metric, kpi_metric_green if reviews else kpi_title_style),
        Paragraph(rating_sub, kpi_sub_style)
    ]

    # 3. Verified Skills Count
    skills_count = len(skills)
    card_skills = [
        Paragraph("Verified Skills", kpi_title_style),
        Paragraph(f"{skills_count}", kpi_metric_style),
        Paragraph("Validated Competencies", kpi_sub_style)
    ]

    # 4. Competency Match Count
    if gaps:
        matched_count = sum(1 for g in gaps if g.get("gap", 0) == 0)
        total_bench = len(gaps)
        match_metric = f"{matched_count} of {total_bench}"
        match_sub = "Target Skills Met"
    elif target_role and target_role != "Not selected":
        match_metric = "All Matched"
        match_sub = "Zero Gaps Identified"
    else:
        match_metric = "Pending"
        match_sub = "Select Benchmark Role"

    card_matches = [
        Paragraph("Competency Matches", kpi_title_style),
        Paragraph(match_metric, kpi_metric_style),
        Paragraph(match_sub, kpi_sub_style)
    ]

    kpi_data = [[card_readiness, '', card_perf, '', card_skills, '', card_matches]]
    kpi_table = Table(kpi_data, colWidths=[124, 9, 124, 9, 124, 9, 124])
    kpi_t_style = [('VALIGN', (0,0), (-1,-1), 'TOP')]
    for col_i in [0, 2, 4, 6]:
        kpi_t_style.extend([
            ('BACKGROUND', (col_i, 0), (col_i, 0), colors.HexColor(card_bg_hex)),
            ('BOX', (col_i, 0), (col_i, 0), 0.5, colors.HexColor(border_hex)),
            ('TOPPADDING', (col_i, 0), (col_i, 0), 4),
            ('BOTTOMPADDING', (col_i, 0), (col_i, 0), 4),
            ('LEFTPADDING', (col_i, 0), (col_i, 0), 6),
            ('RIGHTPADDING', (col_i, 0), (col_i, 0), 6),
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
    elements.append(Spacer(1, 4))

    # --- 1.C: Skills Gap Analysis ---
    elements.append(Paragraph("SKILLS GAP ANALYSIS", section_h1_style))
    if gaps:
        gap_rows = [[
            Paragraph("<b>Skill</b>", table_header_style),
            Paragraph("<b>Current Proficiency</b>", table_header_style),
            Paragraph("<b>Required Proficiency</b>", table_header_style),
            Paragraph("<b>Gap</b>", table_header_style),
            Paragraph("<b>Priority</b>", table_header_style)
        ]]
        for g in gaps:
            pri = str(g.get("priority", "Medium"))
            pri_color = "#DC2626" if pri == "High" else ("#D97706" if pri == "Medium" else "#059669")
            gap_val = int(g.get("gap", 0))
            gap_text = "0 (Met)" if gap_val == 0 else f"-{gap_val} Levels"
            gap_color = "#059669" if gap_val == 0 else "#DC2626"

            cur_lvl = g.get("current", 0)
            req_lvl = g.get("required", 0)

            gap_rows.append([
                Paragraph(_escape_xml(g.get("skill", "Competency")), body_style),
                Paragraph(f"Level {cur_lvl}", body_style),
                Paragraph(f"Level {req_lvl}", body_style),
                Paragraph(f"<font color='{gap_color}'><b>{gap_text}</b></font>", body_style),
                Paragraph(f"<font color='{pri_color}'><b>{_escape_xml(pri)}</b></font>", body_style)
            ])
        gap_table = Table(gap_rows, colWidths=[143, 95, 95, 95, 95])
        gap_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
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
    elements.append(Spacer(1, 4))

    # --- 1.D: Performance Summary ---
    elements.append(Paragraph("PERFORMANCE SUMMARY", section_h1_style))
    if reviews:
        rev_rows = [[
            Paragraph("<b>Review Period</b>", table_header_style),
            Paragraph("<b>Rating</b>", table_header_style),
            Paragraph("<b>Evaluation Date</b>", table_header_style),
            Paragraph("<b>Feedback &amp; Evaluated Accomplishments</b>", table_header_style)
        ]]
        for r in reviews:
            rev_score = float(r.get("performance_score") or 0.0)
            score_col = "#059669" if rev_score >= 4.0 else ("#2563EB" if rev_score >= 3.0 else "#DC2626")
            rev_period = _escape_xml(r.get("review_period") or "Annual Review")
            rev_dt = _escape_xml(str(r.get("review_date") or r.get("created_at") or "Not recorded")[:10])
            ach = _escape_xml(r.get("achievements") or "Key objectives fulfilled.")
            feed = _escape_xml(r.get("manager_feedback") or "Reliable performance across deliverables.")

            rev_rows.append([
                Paragraph(rev_period, body_style),
                Paragraph(f"<font color='{score_col}'><b>{rev_score:.1f} / 5.0</b></font>", bold_style),
                Paragraph(rev_dt, body_style),
                Paragraph(f"<b>Feedback:</b> {feed}<br/><b>Achievements:</b> {ach}", body_style)
            ])
        rev_table = Table(rev_rows, colWidths=[95, 75, 85, 268])
        rev_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for r_idx in range(1, len(rev_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            rev_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        rev_table.setStyle(TableStyle(rev_style))
        elements.append(rev_table)
    else:
        # EXACT PHRASE REQUIRED BY SPEC: "Performance evaluation not yet recorded."
        elements.append(Paragraph("Performance evaluation not yet recorded.", not_recorded_style))

    # ==========================================================================
    # PAGE BREAK: STRICT TWO-PAGE BOUNDARY
    # ==========================================================================
    elements.append(PageBreak())

    # ==========================================================================
    # PAGE 2: CAREER DEVELOPMENT PLAN
    # ==========================================================================

    # --- 2.A: Verified Competencies ---
    elements.append(Paragraph("VERIFIED COMPETENCIES", section_h1_style))
    if skills:
        sk_rows = [[
            Paragraph("<b>Verified Competency</b>", table_header_style),
            Paragraph("<b>Category</b>", table_header_style),
            Paragraph("<b>Proficiency Level</b>", table_header_style),
            Paragraph("<b>Tenure / Experience</b>", table_header_style)
        ]]
        for s in skills:
            s_name = _escape_xml(s.get("name") or s.get("skill_name") or "Skill")
            s_cat = _escape_xml(s.get("category") or "Technical")
            s_prof = _escape_xml(s.get("proficiency") or s.get("proficiency_level") or "Intermediate")
            exp_num = s.get("years_experience") or s.get("years") or 1.0
            s_exp = f"{float(exp_num):g} Yrs"

            sk_rows.append([
                Paragraph(s_name, body_style),
                Paragraph(s_cat, body_style),
                Paragraph(f"<b>{s_prof}</b>", body_style),
                Paragraph(s_exp, body_style)
            ])
        sk_table = Table(sk_rows, colWidths=[163, 120, 120, 120])
        sk_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for r_idx in range(1, len(sk_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            sk_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        sk_table.setStyle(TableStyle(sk_style))
        elements.append(sk_table)
    else:
        elements.append(Paragraph("No verified competencies recorded in employee profile.", not_recorded_style))
    elements.append(Spacer(1, 4))

    # --- 2.B: Development Priorities (Top 3–5 Skill Gaps with Specific Actions) ---
    elements.append(Paragraph("DEVELOPMENT PRIORITIES", section_h1_style))
    active_gaps = [g for g in gaps if g.get("gap", 0) > 0] if gaps else []
    if active_gaps:
        # Sort by gap magnitude and priority
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        sorted_gaps = sorted(active_gaps, key=lambda x: priority_order.get(x.get("priority", "Medium"), 4))[:4]

        prio_rows = [[
            Paragraph("<b>Priority Competency</b>", table_header_style),
            Paragraph("<b>Target Growth</b>", table_header_style),
            Paragraph("<b>Action Plan &amp; Strategic Execution</b>", table_header_style)
        ]]
        for g in sorted_gaps:
            sk_name = _escape_xml(g.get("skill", "Competency"))
            pri_tag = _escape_xml(g.get("priority", "Medium"))
            pri_color = "#DC2626" if pri_tag == "High" else ("#D97706" if pri_tag == "Medium" else "#059669")
            cur_l = g.get("current", 0)
            req_l = g.get("required", 0)

            action_desc = f"Advance competency from Level {cur_l} to Level {req_l} through practical hands-on project delivery, architectural code reviews, and structured certification."

            prio_rows.append([
                Paragraph(f"<b>{sk_name}</b><br/><font color='{pri_color}'><b>[{pri_tag}]</b></font>", body_style),
                Paragraph(f"Level {cur_l} &rarr; Level {req_l}", body_style),
                Paragraph(action_desc, body_style)
            ])
        prio_table = Table(prio_rows, colWidths=[133, 90, 300])
        prio_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for r_idx in range(1, len(prio_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            prio_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        prio_table.setStyle(TableStyle(prio_style))
        elements.append(prio_table)
    else:
        elements.append(Paragraph("No active development priority gaps identified for target role.", not_recorded_style))
    elements.append(Spacer(1, 4))

    # --- 2.C: Career Growth Roadmap ---
    elements.append(Paragraph("CAREER GROWTH ROADMAP", section_h1_style))
    roadmap_rows = [
        [
            Paragraph("<b>Timeline</b>", table_header_style),
            Paragraph("<b>Development Focus</b>", table_header_style),
            Paragraph("<b>Expected Outcome</b>", table_header_style),
            Paragraph("<b>Success Criteria</b>", table_header_style)
        ],
        [
            Paragraph("<b>Months 0–3</b><br/>Foundation", body_style),
            Paragraph("<b>Core Competency Alignment</b>", body_style),
            Paragraph(f"Address priority gaps identified for {target_role}.", body_style),
            Paragraph("Complete technical benchmarks and certifications.", body_style)
        ],
        [
            Paragraph("<b>Months 3–6</b><br/>Execution", body_style),
            Paragraph("<b>Cross-Functional Ownership</b>", body_style),
            Paragraph("Lead core subsystem deliverables and reviews.", body_style),
            Paragraph("Validated manager endorsement and measurable impact.", body_style)
        ],
        [
            Paragraph("<b>Months 6–12</b><br/>Readiness", body_style),
            Paragraph(f"<b>{target_role} Transition</b>", body_style),
            Paragraph(f"Formal promotion review for {target_role}.", body_style),
            Paragraph("Transition into target designation responsibilities.", body_style)
        ]
    ]
    roadmap_table = Table(roadmap_rows, colWidths=[80, 133, 155, 155])
    roadmap_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]
    roadmap_table.setStyle(TableStyle(roadmap_style))
    elements.append(roadmap_table)
    elements.append(Spacer(1, 4))

    # --- 2.D: Goals and Achievements ---
    elements.append(Paragraph("GOALS AND ACHIEVEMENTS", section_h1_style))
    if goals:
        goal_rows = [[
            Paragraph("<b>Milestone Goal Title</b>", table_header_style),
            Paragraph("<b>Target Alignment</b>", table_header_style),
            Paragraph("<b>Target Date</b>", table_header_style),
            Paragraph("<b>Progress</b>", table_header_style),
            Paragraph("<b>Status</b>", table_header_style)
        ]]
        for g in goals[:3]:
            stat = str(g.get("status", "In Progress"))
            stat_color = "#059669" if stat == "Completed" else (sub_accent_hex if stat == "In Progress" else "#DC2626")
            goal_rows.append([
                Paragraph(_escape_xml(g.get("title", "Goal")), body_style),
                Paragraph(_escape_xml(g.get("target_designation") or target_role), body_style),
                Paragraph(_escape_xml(str(g.get("target_date") or "Not recorded")), body_style),
                Paragraph(f"{g.get('progress', 0)}%", body_style),
                Paragraph(f"<font color='{stat_color}'><b>{_escape_xml(stat)}</b></font>", body_style)
            ])
        goal_table = Table(goal_rows, colWidths=[173, 110, 85, 65, 90])
        goal_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for r_idx in range(1, len(goal_rows)):
            bg = '#FFFFFF' if r_idx % 2 == 1 else '#F8FAFC'
            goal_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor(bg)))
        goal_table.setStyle(TableStyle(goal_style))
        elements.append(goal_table)
    else:
        elements.append(Paragraph("No active career goals or milestones recorded.", not_recorded_style))
    elements.append(Spacer(1, 4))

    # --- 2.E: Review and Acknowledgement ---
    elements.append(Paragraph("REVIEW &amp; ACKNOWLEDGEMENT", section_h1_style))
    signoff_rows = [
        [
            Paragraph(f"<b>Employee Acknowledgement</b><br/><br/><br/>___________________________<br/><b>{_escape_xml(user_name)}</b><br/>Date: ____________________", body_style),
            "",
            Paragraph("<b>Reviewing Manager Sign-off</b><br/><br/><br/>___________________________<br/><b>Authorized Evaluator</b><br/>Date: ____________________", body_style),
            "",
            Paragraph("<b>HR Governance Endorsement</b><br/><br/><br/>___________________________<br/><b>Talent Committee Director</b><br/>Date: ____________________", body_style)
        ]
    ]
    signoff_table = Table(signoff_rows, colWidths=[170, 6, 170, 7, 170])
    signoff_style = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for c_i in [0, 2, 4]:
        signoff_style.extend([
            ('BACKGROUND', (c_i, 0), (c_i, 0), colors.HexColor(card_bg_hex)),
            ('BOX', (c_i, 0), (c_i, 0), 0.5, colors.HexColor(border_hex)),
            ('TOPPADDING', (c_i, 0), (c_i, 0), 4),
            ('BOTTOMPADDING', (c_i, 0), (c_i, 0), 4),
            ('LEFTPADDING', (c_i, 0), (c_i, 0), 6),
            ('RIGHTPADDING', (c_i, 0), (c_i, 0), 6),
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
        "<b>CONFIDENTIALITY NOTICE:</b> This dossier contains evaluated corporate talent metrics. "
        "It is intended exclusively for authorized HR personnel and the employee named herein.",
        subtitle_style
    ))

    # --------------------------------------------------------------------------
    # 5. BUILD 2-PAGE DOCUMENT WITH NUMBERED CANVAS
    # --------------------------------------------------------------------------
    doc.build(elements, canvasmaker=make_numbered_canvas(company_name, user_name))
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
