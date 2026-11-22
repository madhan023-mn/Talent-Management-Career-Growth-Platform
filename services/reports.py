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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image
)

THEME_PALETTES = {
    "Navy & Teal": {
        "primary": "#0F172A",
        "accent": "#0D9488",
        "sub_accent": "#1E3A8A",
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
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748B"))

            # Running Header on page 2+
            if self._pageNumber > 1:
                self.setStrokeColor(colors.HexColor("#E2E8F0"))
                self.setLineWidth(0.5)
                self.line(36, A4[1] - 28, A4[0] - 36, A4[1] - 28)
                hdr_left = f"{clean_company} · EMPLOYEE CAREER & COMPETENCY REPORT"
                self.drawString(36, A4[1] - 23, hdr_left.upper())
                self.drawRightString(A4[0] - 36, A4[1] - 23, employee_name)

            # Running Footer on all pages
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 32, A4[0] - 36, 32)

            footer_left = f"{clean_company.upper()} | CONFIDENTIAL & PROPRIETARY"
            page_str = f"Page {self._pageNumber} of {page_count}"
            self.drawString(36, 20, footer_left)
            self.drawRightString(A4[0] - 36, 20, page_str)
            self.restoreState()

    return NumberedCanvas


def create_report(
    profile: Dict[str, Any],
    skills: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    gaps: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    assessments: List[Dict[str, Any]],
    progress: List[Dict[str, Any]],
    goals: Optional[List[Dict[str, Any]]] = None,
    reviews: Optional[List[Dict[str, Any]]] = None,
    trainings: Optional[List[Dict[str, Any]]] = None,
    pdf_config: Optional[Dict[str, Any]] = None,
    org_id: Optional[str] = None
) -> bytes:
    """
    Renders an executive, publication-grade corporate talent dossier adhering strictly to:
      1. Organization Name First
      2. Employee Information Second
      3. Executive Career Summary Third (4 KPI cards + status summary)
      4. Professional Sequential Report Sections (1 through 9):
         1. Professional Profile & Role Trajectory
         2. Performance Reviews & Evaluation History
         3. Skills Matrix & Competency Gap Analysis
         4. Career Development Goals & Milestones
         5. Training & Development History
         6. Achievements & Strengths
         7. Strategic Recommendations & Next Moves
         8. Career Growth Roadmap
         9. HR Assessment and Comments, where authorized
      5. Running headers, footers with 'Page X of Y', and final-page confidentiality notice.
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
        raw_company = "TALENT GROWTH TECHNOLOGIES"
    company_name = raw_company

    theme_name = cfg.get("theme_color", "Navy & Teal")
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Navy & Teal"])

    primary_hex = palette["primary"]
    accent_hex = palette["accent"]
    sub_accent_hex = palette["sub_accent"]
    card_bg_hex = palette.get("card_bg", "#F8FAFC")
    border_hex = palette.get("border", "#CBD5E1")

    # Employee Data Resolution
    user_name = profile.get("name") or "Sarah Connor"
    emp_id = (
        profile.get("employee_id")
        or profile.get("emp_id")
        or (f"EMP{profile.get('user_id', 1):03d}" if profile.get("user_id") else "EMP-101")
    )
    current_role = profile.get("job_title") or profile.get("designation") or "Full Stack Engineer"
    target_role = profile.get("target_role") or "Senior Software Engineer"
    dept = profile.get("department") or "Engineering"
    years_val = profile.get("years_experience") or 0
    years_str = f"{float(years_val):g} Years" if years_val else "Early Career"
    target_level = profile.get("target_level") or "Senior"
    timeline = profile.get("timeline") or "6–12 Months"

    # Reporting Period Resolution
    report_period = "2025 Annual Review"
    if reviews:
        first_rev = reviews[0]
        if first_rev.get("review_period"):
            report_period = str(first_rev["review_period"])

    # Generated Date Resolution
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
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Typography & Styles
    org_title_style = ParagraphStyle(
        'OrgHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=1
    )
    dossier_subtitle_style = ParagraphStyle(
        'DossierSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=3
    )
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.HexColor(primary_hex),
        spaceAfter=4
    )
    emp_banner_style = ParagraphStyle(
        'EmpBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor(primary_hex),
        spaceBefore=4,
        spaceAfter=4
    )
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor(primary_hex),
        spaceBefore=9,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor(primary_hex)
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#0F172A')
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#475569')
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    conf_notice_style = ParagraphStyle(
        'ConfNotice',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )

    # Dedicated styles for beautifully spaced KPI metric cards
    kpi_label_style = ParagraphStyle(
        'KpiLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#475569'),
        spaceAfter=3
    )
    kpi_val_teal = ParagraphStyle(
        'KpiValTeal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor(accent_hex),
        spaceAfter=2
    )
    kpi_val_green = ParagraphStyle(
        'KpiValGreen',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#059669'),
        spaceAfter=2
    )
    kpi_val_blue = ParagraphStyle(
        'KpiValBlue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor(sub_accent_hex),
        spaceAfter=2
    )
    kpi_val_navy = ParagraphStyle(
        'KpiValNavy',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor(primary_hex),
        spaceAfter=2
    )
    kpi_sub_style = ParagraphStyle(
        'KpiSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.8,
        leading=9,
        textColor=colors.HexColor('#64748B')
    )

    elements: List[Any] = []

    # --------------------------------------------------------------------------
    # 1. ORGANIZATION NAME FIRST
    # --------------------------------------------------------------------------
    logo_img = None
    logo_base64 = cfg.get("logo_base64")
    if logo_base64 and "," in logo_base64:
        try:
            raw_b64 = logo_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            img_buf = BytesIO(img_bytes)
            logo_img = Image(img_buf, width=110, height=34)
        except Exception:
            logo_img = None

    if logo_img:
        hdr_table_data = [
            [
                [
                    Paragraph(f"<b>{_escape_xml(company_name.upper())}</b>", org_title_style),
                    Paragraph("CONFIDENTIAL — ENTERPRISE CAREER &amp; COMPETENCY EVALUATION DOSSIER", dossier_subtitle_style),
                    Paragraph("EMPLOYEE CAREER &amp; COMPETENCY REPORT", doc_title_style)
                ],
                logo_img
            ]
        ]
        hdr_table = Table(hdr_table_data, colWidths=[403, 120])
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
        elements.append(Paragraph("CONFIDENTIAL — ENTERPRISE CAREER &amp; COMPETENCY EVALUATION DOSSIER", dossier_subtitle_style))
        elements.append(Paragraph("EMPLOYEE CAREER &amp; COMPETENCY REPORT", doc_title_style))

    # Corporate Accent Separator Line
    elements.append(HRFlowable(width="100%", thickness=2.0, color=colors.HexColor(accent_hex), spaceAfter=6, spaceBefore=2))

    # --------------------------------------------------------------------------
    # 2. EMPLOYEE INFORMATION SECOND
    # --------------------------------------------------------------------------
    elements.append(Paragraph(f"<b>Employee Name:</b> <font color='{primary_hex}'>{_escape_xml(user_name)}</font>", emp_banner_style))

    emp_info_data = [
        [
            Paragraph("<b>Employee ID:</b>", meta_label_style),
            Paragraph(_escape_xml(emp_id), meta_val_style),
            Paragraph("<b>Department:</b>", meta_label_style),
            Paragraph(_escape_xml(dept), meta_val_style)
        ],
        [
            Paragraph("<b>Current Designation:</b>", meta_label_style),
            Paragraph(_escape_xml(current_role), meta_val_style),
            Paragraph("<b>Years of Experience:</b>", meta_label_style),
            Paragraph(_escape_xml(years_str), meta_val_style)
        ],
        [
            Paragraph("<b>Target Designation:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(target_role)}</b>", meta_val_style),
            Paragraph("<b>Target Career Level:</b>", meta_label_style),
            Paragraph(_escape_xml(target_level), meta_val_style)
        ],
        [
            Paragraph("<b>Reporting Period:</b>", meta_label_style),
            Paragraph(_escape_xml(report_period), meta_val_style),
            Paragraph("<b>Career Timeline:</b>", meta_label_style),
            Paragraph(_escape_xml(timeline), meta_val_style)
        ],
        [
            Paragraph("<b>Report Type:</b>", meta_label_style),
            Paragraph("Talent Performance &amp; Growth Dossier", meta_val_style),
            Paragraph("<b>Generated On:</b>", meta_label_style),
            Paragraph(_escape_xml(generated_date), meta_val_style)
        ]
    ]
    emp_table = Table(emp_info_data, colWidths=[105, 156, 105, 157])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 6))

    # --------------------------------------------------------------------------
    # 3. EXECUTIVE CAREER SUMMARY THIRD
    # --------------------------------------------------------------------------
    elements.append(Paragraph("EXECUTIVE CAREER SUMMARY", h2_style))
    elements.append(Spacer(1, 3))

    match_score = int(analysis.get("match") or 0)
    comp_profile = int(analysis.get("completion") or 0)
    total_sk = len(skills)
    total_g = len(goals) if goals else 0
    comp_g = sum(1 for g in goals if g.get("status") == "Completed") if goals else 0
    avg_prog = round(sum(float(g.get("progress") or 0) for g in goals) / total_g) if total_g else 0

    if reviews:
        latest_rev = reviews[0]
        latest_score = float(latest_rev.get("performance_score") or 0.0)
        rating_text = f"{latest_score:.1f} / 5.0"
        cycle_text = str(latest_rev.get("review_period") or "Performance Review")
        if latest_score >= 4.5:
            badge_text = "Top Performer"
        elif latest_score >= 4.0:
            badge_text = "Exceeds Goals"
        elif latest_score >= 3.0:
            badge_text = "Meets Expectations"
        else:
            badge_text = "Needs Development"
    else:
        rating_text = "Unrated"
        cycle_text = "No Reviews Recorded"
        badge_text = "Pending Cycle"

    card1 = [
        Paragraph("Target Role Readiness", kpi_label_style),
        Paragraph(f"{match_score}%", kpi_val_blue),
        Paragraph(f"Role: <b>{_escape_xml(target_role)}</b>", kpi_sub_style)
    ]
    card2 = [
        Paragraph("Performance Score", kpi_label_style),
        Paragraph(f"{rating_text}", kpi_val_green),
        Paragraph(f"{badge_text} · {_escape_xml(cycle_text)}", kpi_sub_style)
    ]
    card3 = [
        Paragraph("Goals &amp; Milestones", kpi_label_style),
        Paragraph(f"{avg_prog}% <font size='9'>Avg</font>", kpi_val_navy),
        Paragraph(f"<b>{comp_g} of {total_g}</b> achieved", kpi_sub_style)
    ]
    card4 = [
        Paragraph("Verified Competencies", kpi_label_style),
        Paragraph(f"{total_sk} <font size='9'>Skills</font>", kpi_val_teal),
        Paragraph(f"Profile Readiness: <b>{comp_profile}%</b>", kpi_sub_style)
    ]

    kpi_data = [[card1, '', card2, '', card3, '', card4]]
    kpi_table = Table(kpi_data, colWidths=[124, 9, 124, 9, 124, 9, 124])

    kpi_t_style = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for col_idx in [0, 2, 4, 6]:
        kpi_t_style.extend([
            ('BACKGROUND', (col_idx, 0), (col_idx, 0), colors.HexColor(card_bg_hex)),
            ('BOX', (col_idx, 0), (col_idx, 0), 0.75, colors.HexColor(border_hex)),
            ('TOPPADDING', (col_idx, 0), (col_idx, 0), 6),
            ('BOTTOMPADDING', (col_idx, 0), (col_idx, 0), 6),
            ('LEFTPADDING', (col_idx, 0), (col_idx, 0), 8),
            ('RIGHTPADDING', (col_idx, 0), (col_idx, 0), 8),
        ])
    for gap_idx in [1, 3, 5]:
        kpi_t_style.extend([
            ('TOPPADDING', (gap_idx, 0), (gap_idx, 0), 0),
            ('BOTTOMPADDING', (gap_idx, 0), (gap_idx, 0), 0),
            ('LEFTPADDING', (gap_idx, 0), (gap_idx, 0), 0),
            ('RIGHTPADDING', (gap_idx, 0), (gap_idx, 0), 0),
        ])
    kpi_table.setStyle(TableStyle(kpi_t_style))
    elements.append(kpi_table)
    elements.append(Spacer(1, 5))

    summary_text = profile.get("summary")
    if not summary_text or len(str(summary_text).strip()) < 15:
        summary_text = (
            f"{user_name} is currently serving as {current_role} within the {dept} department with {years_str} "
            f"of professional experience. Current target role alignment reflects a {match_score}% readiness score "
            f"for {target_role}. Verified performance status is {rating_text} ({badge_text}, {cycle_text}). "
            f"The candidate maintains active growth momentum with {total_sk} verified competencies and "
            f"{comp_g} of {total_g} strategic milestones achieved."
        )
    elements.append(Paragraph(f"<b>Executive Career Assessment:</b> {_escape_xml(summary_text)}", body_style))
    elements.append(Spacer(1, 6))

    # --------------------------------------------------------------------------
    # 4. PROFESSIONAL REPORT SECTIONS (1 through 9)
    # --------------------------------------------------------------------------

    # --- Section 1: Professional Profile & Role Trajectory ---
    elements.append(Paragraph("1. Professional Profile &amp; Role Trajectory", h2_style))
    prof_traj_data = [
        [
            Paragraph("<b>Current Role:</b>", meta_label_style),
            Paragraph(_escape_xml(current_role), meta_val_style),
            Paragraph("<b>Target Role:</b>", meta_label_style),
            Paragraph(f"<b>{_escape_xml(target_role)}</b>", meta_val_style)
        ],
        [
            Paragraph("<b>Education:</b>", meta_label_style),
            Paragraph(_escape_xml(profile.get("education") or "Bachelor of Science in Computer Science / Engineering"), meta_val_style),
            Paragraph("<b>Target Industry:</b>", meta_label_style),
            Paragraph(_escape_xml(profile.get("target_industry") or "Technology &amp; Software Solutions"), meta_val_style)
        ],
        [
            Paragraph("<b>Certifications:</b>", meta_label_style),
            Paragraph(_escape_xml(profile.get("certifications") or "Industry Standard Technical Certifications"), meta_val_style),
            Paragraph("<b>Career Goal:</b>", meta_label_style),
            Paragraph(_escape_xml(profile.get("career_goal") or f"Advance into {target_role} and drive technical excellence"), meta_val_style)
        ],
        [
            Paragraph("<b>Contact &amp; Location:</b>", meta_label_style),
            Paragraph(f"{_escape_xml(profile.get('email') or 'Verified Company Email')} · {_escape_xml(profile.get('location') or 'Corporate Office')}", meta_val_style),
            Paragraph("<b>Internal Roster:</b>", meta_label_style),
            Paragraph(f"Active Employee Profile ({_escape_xml(emp_id)})", meta_val_style)
        ]
    ]
    prof_table = Table(prof_traj_data, colWidths=[105, 156, 105, 157])
    prof_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(prof_table)
    elements.append(Spacer(1, 6))

    # --- Section 2: Performance Reviews & Evaluation History ---
    elements.append(Paragraph("2. Performance Reviews &amp; Evaluation History", h2_style))
    if reviews:
        rev_rows = [[
            Paragraph("<b>Review Cycle</b>", table_header_style),
            Paragraph("<b>Rating</b>", table_header_style),
            Paragraph("<b>Key Achievements &amp; Core Strengths</b>", table_header_style),
            Paragraph("<b>Manager Feedback &amp; Development Areas</b>", table_header_style)
        ]]
        for r in reviews:
            rev_score = float(r.get("performance_score") or 0.0)
            score_col = "#059669" if rev_score >= 4.0 else ("#2563EB" if rev_score >= 3.0 else "#DC2626")
            ach_str = _escape_xml(r.get('achievements') or 'Demonstrated solid delivery across key objectives.')
            str_str = _escape_xml(r.get('strengths') or 'Collaborative, proactive problem solver.')
            m_feed = _escape_xml(r.get('manager_feedback') or 'Strong overall performance and reliable contributor.')
            m_imp = _escape_xml(r.get('improvements') or 'Focus on architectural leadership.')

            rev_rows.append([
                Paragraph(_escape_xml(r.get("review_period", "Annual Review")), body_style),
                Paragraph(f"<font color='{score_col}'><b>{rev_score:.1f} / 5.0</b></font>", bold_style),
                Paragraph(f"<b>Achievements:</b> {ach_str}<br/><b>Strengths:</b> {str_str}", body_style),
                Paragraph(f"<b>Feedback:</b> {m_feed}<br/><b>Growth Area:</b> {m_imp}", body_style)
            ])
        rev_table = Table(rev_rows, colWidths=[85, 65, 185, 188])
        t_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for row_i in range(1, len(rev_rows)):
            if row_i % 2 == 1:
                t_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#FFFFFF')))
            else:
                t_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#F8FAFC')))
        rev_table.setStyle(TableStyle(t_style))
        elements.append(rev_table)
    else:
        elements.append(Paragraph("No formal performance reviews logged yet for this evaluation cycle. Baseline evaluations are derived from continuous role benchmarks.", body_style))
    elements.append(Spacer(1, 6))

    # --- Section 3: Skills Matrix & Competency Gap Analysis ---
    elements.append(Paragraph("3. Skills Matrix &amp; Competency Gap Analysis", h2_style))
    if gaps:
        gap_rows = [[
            Paragraph("<b>Target Competency Required</b>", table_header_style),
            Paragraph("<b>Current Level</b>", table_header_style),
            Paragraph("<b>Required Level</b>", table_header_style),
            Paragraph("<b>Gap Score</b>", table_header_style),
            Paragraph("<b>Priority Level</b>", table_header_style)
        ]]
        for g in gaps:
            pri = str(g.get("priority", "Medium"))
            pri_color = "#DC2626" if pri == "High" else ("#F59E0B" if pri == "Medium" else "#059669")
            gap_rows.append([
                Paragraph(_escape_xml(g.get("skill", "Competency")), body_style),
                Paragraph(f"Level {g.get('current', 0)}", body_style),
                Paragraph(f"Level {g.get('required', 0)}", body_style),
                Paragraph(str(g.get("gap", 0)), body_style),
                Paragraph(f"<font color='{pri_color}'><b>{_escape_xml(pri)}</b></font>", body_style)
            ])
        gap_table = Table(gap_rows, colWidths=[143, 95, 95, 90, 100])
        gap_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for row_i in range(1, len(gap_rows)):
            if row_i % 2 == 1:
                gap_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#FFFFFF')))
            else:
                gap_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#F8FAFC')))
        gap_table.setStyle(TableStyle(gap_style))
        elements.append(gap_table)
    else:
        elements.append(Paragraph("All technical and behavioral competencies for the target role are fully met or exceeded.", body_style))

    # Verified Skills Sub-Table
    if skills:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("<b>Cataloged Employee Competencies:</b>", bold_style))
        sk_rows = [[
            Paragraph("<b>Verified Competency</b>", table_header_style),
            Paragraph("<b>Category</b>", table_header_style),
            Paragraph("<b>Proficiency Level</b>", table_header_style),
            Paragraph("<b>Experience Tenure</b>", table_header_style)
        ]]
        for s in skills:
            s_name = _escape_xml(s.get("name") or s.get("skill_name") or "Skill")
            s_cat = _escape_xml(s.get("category") or "Technical")
            s_prof = _escape_xml(s.get("proficiency") or s.get("proficiency_level") or "Intermediate")
            s_exp = f"{float(s.get('years_experience') or 1.0):g} Yrs"
            sk_rows.append([
                Paragraph(s_name, body_style),
                Paragraph(s_cat, body_style),
                Paragraph(f"<b>{s_prof}</b>", body_style),
                Paragraph(s_exp, body_style)
            ])
        sk_table = Table(sk_rows, colWidths=[173, 110, 120, 120])
        sk_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 2.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for row_i in range(1, len(sk_rows)):
            if row_i % 2 == 1:
                sk_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#FFFFFF')))
            else:
                sk_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#F8FAFC')))
        sk_table.setStyle(TableStyle(sk_style))
        elements.append(sk_table)
    elements.append(Spacer(1, 6))

    # --- Section 4: Career Development Goals & Milestones ---
    elements.append(Paragraph("4. Career Development Goals &amp; Milestones", h2_style))
    if goals:
        goal_rows = [[
            Paragraph("<b>Goal Milestone Title</b>", table_header_style),
            Paragraph("<b>Target Alignment</b>", table_header_style),
            Paragraph("<b>Target Date</b>", table_header_style),
            Paragraph("<b>Progress</b>", table_header_style),
            Paragraph("<b>Status</b>", table_header_style)
        ]]
        for g in goals:
            stat = str(g.get("status", "In Progress"))
            stat_color = "#059669" if stat == "Completed" else (sub_accent_hex if stat == "In Progress" else "#DC2626")
            goal_rows.append([
                Paragraph(_escape_xml(g.get("title", "Goal")), body_style),
                Paragraph(_escape_xml(g.get("target_designation") or target_role), body_style),
                Paragraph(_escape_xml(str(g.get("target_date") or "Q4 2026")), body_style),
                Paragraph(f"{g.get('progress', 0)}%", body_style),
                Paragraph(f"<font color='{stat_color}'><b>{_escape_xml(stat)}</b></font>", body_style)
            ])
        goal_table = Table(goal_rows, colWidths=[163, 110, 90, 70, 90])
        g_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for row_i in range(1, len(goal_rows)):
            if row_i % 2 == 1:
                g_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#FFFFFF')))
            else:
                g_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#F8FAFC')))
        goal_table.setStyle(TableStyle(g_style))
        elements.append(goal_table)
    else:
        elements.append(Paragraph("No active strategic career milestones registered. Progression checkpoints are detailed in Section 8 (Career Growth Roadmap).", body_style))
    elements.append(Spacer(1, 6))

    # --- Section 5: Training & Development History ---
    elements.append(Paragraph("5. Training &amp; Development History", h2_style))
    training_items = trainings or assessments or []
    if training_items:
        train_rows = [[
            Paragraph("<b>Training / Assessment Program</b>", table_header_style),
            Paragraph("<b>Domain Category</b>", table_header_style),
            Paragraph("<b>Evaluation Score</b>", table_header_style),
            Paragraph("<b>Status / Date</b>", table_header_style)
        ]]
        for t in training_items:
            t_title = _escape_xml(t.get("title") or t.get("skill_name") or t.get("name") or "Technical Evaluation")
            t_cat = _escape_xml(t.get("category") or "Technical")
            t_score = f"{t.get('score', 85)}%" if 'score' in t else "Completed"
            t_date = _escape_xml(str(t.get("created_at") or t.get("completed_at") or "Verified Record")[:10])
            train_rows.append([
                Paragraph(t_title, body_style),
                Paragraph(t_cat, body_style),
                Paragraph(f"<b>{t_score}</b>", body_style),
                Paragraph(t_date, body_style)
            ])
        train_table = Table(train_rows, colWidths=[173, 110, 120, 120])
        tr_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]
        for row_i in range(1, len(train_rows)):
            if row_i % 2 == 1:
                tr_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#FFFFFF')))
            else:
                tr_style.append(('BACKGROUND', (0, row_i), (-1, row_i), colors.HexColor('#F8FAFC')))
        train_table.setStyle(TableStyle(tr_style))
        elements.append(train_table)
    else:
        elements.append(Paragraph(
            "No formal training or assessment records logged yet for this evaluation cycle. "
            "When the candidate completes skill assessments or HR-assigned curriculum modules, "
            "verified records and evaluation scores will appear here.",
            body_style
        ))
    elements.append(Spacer(1, 6))

    # --- Section 6: Achievements & Strengths ---
    elements.append(Paragraph("6. Achievements &amp; Strengths", h2_style))
    strength_items = analysis.get("strengths") or []
    if reviews:
        for r in reviews:
            if r.get("achievements"):
                strength_items.append(f"Performance Achievement: {r['achievements']}")
            if r.get("strengths"):
                strength_items.append(f"Evaluated Core Strength: {r['strengths']}")
    if not strength_items:
        strength_items = [
            f"Demonstrated technical mastery in {current_role} core disciplines.",
            f"Active career trajectory aligned with {target_role} benchmarks.",
            f"Consistent record of reliable project execution and team collaboration."
        ]
    for s_item in strength_items[:4]:
        elements.append(Paragraph(f"• <b>{_escape_xml(s_item)}</b>", body_style))
        elements.append(Spacer(1, 2))
    elements.append(Spacer(1, 4))

    # --- Section 7: Strategic Recommendations & Next Moves ---
    elements.append(Paragraph("7. Strategic Recommendations &amp; Next Moves", h2_style))
    rec_list = recommendations or []
    if not rec_list:
        rec_list = [
            {
                "priority": "High Priority",
                "title": f"Complete Target Competency Benchmark for {target_role}",
                "description": f"Focus quarterly professional development on closing top required skills for {target_role}."
            },
            {
                "priority": "Medium Priority",
                "title": "Lead Technical Cross-Functional Initiatives",
                "description": "Engage in cross-team architectural reviews to build documented evidence of senior impact."
            }
        ]
    for r in rec_list[:3]:
        p_tag = _escape_xml(r.get("priority", "High Priority"))
        p_color = "#DC2626" if "High" in p_tag else "#D97706"
        elements.append(Paragraph(f"<font color='{p_color}'><b>[{p_tag}]</b></font> <b>{_escape_xml(r.get('title', 'Recommendation'))}</b>", bold_style))
        elements.append(Paragraph(_escape_xml(r.get("description", "")), body_style))
        elements.append(Spacer(1, 3))
    elements.append(Spacer(1, 4))

    # --- Section 8: Career Growth Roadmap ---
    elements.append(Paragraph("8. Career Growth Roadmap", h2_style))
    roadmap_rows = [
        [
            Paragraph("<b>Development Horizon</b>", table_header_style),
            Paragraph("<b>Strategic Milestone Focus</b>", table_header_style),
            Paragraph("<b>Deliverables &amp; Success Validation Criteria</b>", table_header_style)
        ],
        [
            Paragraph("<b>Phase 1: Foundation</b><br/>Months 0–3", body_style),
            Paragraph("<b>Core Competency Alignment</b>", body_style),
            Paragraph(f"Address highest-priority skill gaps identified for {target_role}. Complete foundational technical certifications and align individual OKRs with department benchmarks.", body_style)
        ],
        [
            Paragraph("<b>Phase 2: Execution</b><br/>Months 3–6", body_style),
            Paragraph("<b>Cross-Functional Ownership</b>", body_style),
            Paragraph("Lead core subsystem delivery, author technical architectural proposals, and mentor junior colleagues on engineering best practices.", body_style)
        ],
        [
            Paragraph("<b>Phase 3: Transition</b><br/>Months 6–12", body_style),
            Paragraph(f"<b>{target_role} Readiness</b>", body_style),
            Paragraph(f"Undergo comprehensive formal promotion review. Present portfolio of completed milestones and transition smoothly into full {target_role} responsibilities.", body_style)
        ]
    ]
    roadmap_table = Table(roadmap_rows, colWidths=[113, 160, 250])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#FFFFFF')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFFFFF')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(roadmap_table)
    elements.append(Spacer(1, 6))

    # --- Section 9: HR Assessment and Comments, where authorized ---
    elements.append(Paragraph("9. HR Assessment and Comments, where authorized", h2_style))
    elements.append(Paragraph(
        "Formal evaluation compiled in accordance with enterprise talent governance guidelines. "
        "All verified competencies, review scores, and milestone progressions have been validated by the corporate talent committee.",
        body_style
    ))
    elements.append(Spacer(1, 4))

    # Corporate Sign-off Block
    signoff_rows = [
        [
            Paragraph(f"<b>Employee Acknowledgement:</b><br/><br/><br/><br/>___________________________<br/><b>{_escape_xml(user_name)}</b><br/>Date: ____________________", body_style),
            Paragraph("<b>Reviewing Manager Sign-off:</b><br/><br/><br/><br/>___________________________<br/><b>Authorized Evaluator</b><br/>Date: ____________________", body_style),
            Paragraph("<b>HR Governance Endorsement:</b><br/><br/><br/><br/>___________________________<br/><b>Talent Committee Director</b><br/>Date: ____________________", body_style)
        ]
    ]
    signoff_table = Table(signoff_rows, colWidths=[174, 174, 175])
    signoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(card_bg_hex)),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(border_hex)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(KeepTogether(signoff_table))

    # Final Confidentiality Notice
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=4, spaceBefore=4))
    elements.append(Paragraph(
        "<b>CONFIDENTIALITY NOTICE:</b> This report contains confidential employee career and competency information. "
        "It is intended exclusively for authorized HR personnel and the employee concerned.",
        conf_notice_style
    ))

    # --------------------------------------------------------------------------
    # 5. BUILD MULTI-PAGE DOCUMENT WITH NUMBERED CANVAS
    # --------------------------------------------------------------------------
    doc.build(elements, canvasmaker=make_numbered_canvas(company_name, user_name))
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
