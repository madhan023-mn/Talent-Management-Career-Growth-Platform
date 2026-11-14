from __future__ import annotations
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
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
        "card_bg": "#F0FDFA",
        "border": "#CCFBF1"
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
    # Resolve PDF Branding Configuration
    if not pdf_config and org_id:
        try:
            from services.settings import get_org_pdf_config
            pdf_config = get_org_pdf_config(org_id)
        except Exception:
            pdf_config = {}

    cfg = pdf_config or {}
    theme_name = cfg.get("theme_color", "Navy & Teal")
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Navy & Teal"])

    primary_hex = palette["primary"]
    accent_hex = palette["accent"]
    sub_accent_hex = palette["sub_accent"]

    company_name = cfg.get("company_name", "Talent Growth Technologies")
    report_title_pref = cfg.get("report_title", "Talent Intelligence & Career Dossier")
    header_text = cfg.get("header_text", "CONFIDENTIAL — TALENT GROWTH ENTERPRISE")
    footer_text = cfg.get("footer_text", "Talent Growth Platform · Confidential & Proprietary")
    confidentiality = cfg.get("confidentiality_notice", "This document contains confidential talent assessment and career development data. Unauthorized distribution is prohibited.")
    date_format = cfg.get("date_format", "%B %d, %Y")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Dynamic Custom Typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(primary_hex),
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=8
    )
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor(sub_accent_hex),
        spaceBefore=9,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor(primary_hex)
    )
    header_bar_style = ParagraphStyle(
        'HeaderBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#94A3B8')
    )
    footer_style = ParagraphStyle(
        'FooterNotice',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#94A3B8'),
        alignment=1  # Centered
    )

    elements = []

    # 1. Top Header Banner & Organization Branding
    if header_text:
        elements.append(Paragraph(header_text.upper(), header_bar_style))
        elements.append(Spacer(1, 4))

    # Organization Logo or Header Table
    user_name = profile.get("name") or "Employee Talent Dossier"
    target_role = profile.get("target_role") or "Not Specified"

    logo_img = None
    logo_base64 = cfg.get("logo_base64")
    if logo_base64 and "," in logo_base64:
        try:
            raw_b64 = logo_base64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            img_buf = BytesIO(img_bytes)
            logo_img = Image(img_buf, width=100, height=32)
        except Exception:
            logo_img = None

    now = datetime.now()
    try:
        generated_date = now.strftime(date_format)
    except Exception:
        generated_date = now.strftime("%B %d, %Y")

    if logo_img:
        hdr_table_data = [
            [
                logo_img,
                [
                    Paragraph(f"<b>{company_name}</b>", bold_style),
                    Paragraph(f"<font size=15 color='{primary_hex}'><b>{report_title_pref}</b></font>", title_style),
                    Paragraph(f"Subject: <b>{user_name}</b> · Target: <b>{target_role}</b> · Generated: {generated_date}", subtitle_style)
                ]
            ]
        ]
        hdr_table = Table(hdr_table_data, colWidths=[110, 420])
        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(hdr_table)
    else:
        elements.append(Paragraph(f"<font color='{accent_hex}'><b>{company_name}</b></font>", subtitle_style))
        elements.append(Paragraph(f"{report_title_pref}: {user_name}", title_style))
        elements.append(Paragraph(f"Generated on {generated_date} · Comprehensive Talent Performance & Career Growth Report", subtitle_style))

    # Accent Separator Line
    elements.append(HRFlowable(width="100%", thickness=2.0, color=colors.HexColor(accent_hex), spaceAfter=8, spaceBefore=4))

    # 2. Executive Metrics Table
    completion = analysis.get("completion", 0)
    score = analysis.get("score", 0)
    match = analysis.get("match", 0)
    skill_count = len(skills)

    metrics_data = [
        [
            Paragraph(f"<b>Profile Readiness</b><br/><font size=13 color='{accent_hex}'><b>{completion}%</b></font>", body_style),
            Paragraph(f"<b>Competency Score</b><br/><font size=13 color='#10B981'><b>{score}/100</b></font>", body_style),
            Paragraph(f"<b>Target Role Match</b><br/><font size=13 color='{sub_accent_hex}'><b>{match}%</b></font>", body_style),
            Paragraph(f"<b>Skills Cataloged</b><br/><font size=13 color='{primary_hex}'><b>{skill_count}</b></font>", body_style)
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[130, 130, 135, 135])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 8))

    # 3. Profile Overview
    elements.append(Paragraph("1. Professional Profile & Role Trajectory", h2_style))
    profile_info = [
        [Paragraph("<b>Current Role:</b>", body_style), Paragraph(profile.get("job_title") or "Not provided", body_style),
         Paragraph("<b>Target Role:</b>", body_style), Paragraph(target_role, body_style)],
        [Paragraph("<b>Department:</b>", body_style), Paragraph(profile.get("department") or "Not provided", body_style),
         Paragraph("<b>Target Level:</b>", body_style), Paragraph(profile.get("target_level") or "Senior", body_style)],
        [Paragraph("<b>Experience:</b>", body_style), Paragraph(f"{profile.get('years_experience', 0)} years", body_style),
         Paragraph("<b>Target Timeline:</b>", body_style), Paragraph(profile.get("timeline") or "6–12 months", body_style)],
    ]
    p_table = Table(profile_info, colWidths=[85, 180, 85, 180])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFFFF')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(p_table)

    if profile.get("summary"):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("<b>Professional Summary:</b>", bold_style))
        elements.append(Paragraph(profile.get("summary"), body_style))

    # 4. Performance Reviews Section
    if reviews:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("2. Performance Reviews & Evaluation History", h2_style))
        rev_rows = [[
            Paragraph("<b>Period</b>", bold_style),
            Paragraph("<b>Score</b>", bold_style),
            Paragraph("<b>Achievements & Strengths</b>", bold_style),
            Paragraph("<b>Manager Feedback</b>", bold_style)
        ]]
        for r in reviews:
            rev_rows.append([
                Paragraph(r["review_period"], body_style),
                Paragraph(f"<font color='{accent_hex}'><b>{r['performance_score']}/5.0</b></font>", body_style),
                Paragraph(f"<b>Key:</b> {r.get('achievements', '')}<br/><b>Strength:</b> {r.get('strengths', '')}", body_style),
                Paragraph(r.get("manager_feedback", "") or "No feedback recorded", body_style)
            ])
        rev_table = Table(rev_rows, colWidths=[80, 60, 210, 180])
        rev_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(rev_table)

    # 5. Skills Matrix & Gap Analysis
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("3. Skills Matrix & Competency Gap Analysis", h2_style))
    if gaps:
        gap_rows = [[
            Paragraph("<b>Competency Required</b>", bold_style),
            Paragraph("<b>Current Level</b>", bold_style),
            Paragraph("<b>Required Level</b>", bold_style),
            Paragraph("<b>Gap</b>", bold_style),
            Paragraph("<b>Priority</b>", bold_style)
        ]]
        for g in gaps:
            pri_color = "#DC2626" if g["priority"] == "High" else ("#F59E0B" if g["priority"] == "Medium" else "#10B981")
            gap_rows.append([
                Paragraph(g["skill"], body_style),
                Paragraph(str(g["current"]), body_style),
                Paragraph(str(g["required"]), body_style),
                Paragraph(str(g["gap"]), body_style),
                Paragraph(f"<font color='{pri_color}'><b>{g['priority']}</b></font>", body_style)
            ])
        gap_table = Table(gap_rows, colWidths=[150, 95, 95, 90, 100])
        gap_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(gap_table)
    else:
        elements.append(Paragraph("All current required competencies for the target role are fully met or exceeded.", body_style))

    # 6. Career Goals & Training Records
    if goals:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("4. Strategic Career Milestones & Progress", h2_style))
        goal_rows = [[
            Paragraph("<b>Goal Milestone</b>", bold_style),
            Paragraph("<b>Target Role</b>", bold_style),
            Paragraph("<b>Target Date</b>", bold_style),
            Paragraph("<b>Progress</b>", bold_style),
            Paragraph("<b>Status</b>", bold_style)
        ]]
        for g in goals:
            stat_color = "#10B981" if g["status"] == "Completed" else (accent_hex if g["status"] == "In Progress" else "#64748B")
            goal_rows.append([
                Paragraph(g["title"], body_style),
                Paragraph(g.get("target_designation") or "Not Specified", body_style),
                Paragraph(str(g["target_date"]), body_style),
                Paragraph(f"{g['progress']}%", body_style),
                Paragraph(f"<font color='{stat_color}'><b>{g['status']}</b></font>", body_style)
            ])
        goal_table = Table(goal_rows, colWidths=[170, 120, 90, 60, 90])
        goal_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(goal_table)

    if recommendations:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("5. Strategic Recommendations & Next Moves", h2_style))
        for r in recommendations[:3]:
            elements.append(Paragraph(f"<b>[{r['priority']}] {r['title']}</b>", bold_style))
            elements.append(Paragraph(r['description'], body_style))
            elements.append(Spacer(1, 3))

    # 7. Confidentiality Notice & Footer
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1'), spaceAfter=6, spaceBefore=4))
    if confidentiality:
        elements.append(Paragraph(f"<b>Confidentiality Notice:</b> {confidentiality}", footer_style))
        elements.append(Spacer(1, 3))
    if footer_text:
        elements.append(Paragraph(footer_text, footer_style))

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
