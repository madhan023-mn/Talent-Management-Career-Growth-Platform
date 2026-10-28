from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)

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
    trainings: Optional[List[Dict[str, Any]]] = None
) -> bytes:
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

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569'),
        spaceAfter=10
    )
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
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
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # Title & Header
    user_name = profile.get("name") or "Employee Talent Dossier"
    target_role = profile.get("target_role") or "Not Specified"
    elements.append(Paragraph(f"Talent Growth Dossier: {user_name}", title_style))
    generated_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on {generated_date} · Comprehensive Talent Performance & Career Growth Report", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=8))

    # Executive Metrics Table
    completion = analysis.get("completion", 0)
    score = analysis.get("score", 0)
    match = analysis.get("match", 0)
    skill_count = len(skills)

    metrics_data = [
        [
            Paragraph(f"<b>Profile Readiness</b><br/><font size=13 color='#2563EB'><b>{completion}%</b></font>", body_style),
            Paragraph(f"<b>Competency Score</b><br/><font size=13 color='#10B981'><b>{score}/100</b></font>", body_style),
            Paragraph(f"<b>Target Role Match</b><br/><font size=13 color='#6366F1'><b>{match}%</b></font>", body_style),
            Paragraph(f"<b>Skills Cataloged</b><br/><font size=13 color='#0F172A'><b>{skill_count}</b></font>", body_style)
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

    # 1. Profile Overview
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

    # 2. Performance Reviews Section
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
                Paragraph(f"<font color='#2563EB'><b>{r['performance_score']}/5.0</b></font>", body_style),
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

    # 3. Skills Matrix & Gap Analysis
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
        levels_map = {0: "None", 1: "Beginner", 2: "Intermediate", 3: "Advanced", 4: "Expert"}
        for g in gaps:
            color = "#EF4444" if g["priority"] == "High" else ("#F59E0B" if g["priority"] == "Medium" else "#10B981")
            gap_rows.append([
                Paragraph(g["skill"], body_style),
                Paragraph(levels_map.get(g["current"], str(g["current"])), body_style),
                Paragraph(levels_map.get(g["required"], str(g["required"])), body_style),
                Paragraph(str(g["gap"]), body_style),
                Paragraph(f"<font color='{color}'><b>{g['priority']}</b></font>", body_style)
            ])
        gap_table = Table(gap_rows, colWidths=[160, 95, 95, 60, 120])
        gap_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(gap_table)
    elif skills:
        skill_rows = [[Paragraph("<b>Skill</b>", bold_style), Paragraph("<b>Category</b>", bold_style), Paragraph("<b>Proficiency</b>", bold_style), Paragraph("<b>Experience</b>", bold_style)]]
        for s in skills:
            skill_rows.append([
                Paragraph(s.get("name") or s.get("skill_name") or "Skill", body_style),
                Paragraph(s.get("category") or "Technical", body_style),
                Paragraph(s.get("proficiency") or s.get("proficiency_level") or "Intermediate", body_style),
                Paragraph(f"{s.get('years', s.get('years_exp', 1.0))} yrs", body_style)
            ])
        s_table = Table(skill_rows, colWidths=[180, 120, 120, 110])
        s_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2F6')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(s_table)

    # 4. Training & Career Goals Roadmap
    if goals:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("4. Career Development Goals & Milestones", h2_style))
        goal_rows = [[
            Paragraph("<b>Goal Title</b>", bold_style),
            Paragraph("<b>Target Designation</b>", bold_style),
            Paragraph("<b>Target Date</b>", bold_style),
            Paragraph("<b>Progress</b>", bold_style),
            Paragraph("<b>Status</b>", bold_style)
        ]]
        for g in goals:
            stat_color = "#10B981" if g["status"] == "Completed" else ("#2563EB" if g["status"] == "In Progress" else "#64748B")
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

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
