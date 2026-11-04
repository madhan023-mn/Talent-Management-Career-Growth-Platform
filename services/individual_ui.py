"""
Individual Professional User Experience Module
Comprehensive UI components for Individual Registration, Personal Profile,
Skill Management, MCQ Assessments with instant evaluation, Skill Gap Analysis,
Personal Career Goals, and Organization Transitioning.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Callable

from services.core import (
    ROLE_CATALOG, LEVELS,
    get_profile, save_profile, list_skills, add_skill, update_skill, delete_skill,
    get_assessments, get_goals, get_goal_by_id, add_goal, update_goal, update_goal_progress, delete_goal, get_goal_stats,
    SKILL_ASSESSMENT_BANK, get_available_assessments, get_assessment_questions,
    evaluate_assessment, get_skill_assessment_history,
    join_organization, get_individual_dashboard_stats, validate_invitation_code
)


def _render_html(html_str: str) -> None:
    """Render clean HTML without indentation issues."""
    clean_html = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean_html, unsafe_allow_html=True)


def _get_svg_icon(name: str, size: int = 18, color: str = "#4F46E5") -> str:
    icons = {
        "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
        "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
        "award": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
        "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
        "cross": '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        "briefcase": '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
        "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        "building": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
        "trending_up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
        "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
        "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
        "edit": '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>',
        "arrow_right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
        "calendar": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
        "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
    }
    path_data = icons.get(name, icons["sparkles"])
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;">{path_data}</svg>'


# ==============================================================================
# SECTION 3A: DEDICATED INDIVIDUAL USER DASHBOARD OVERVIEW
# ==============================================================================
def render_individual_dashboard(user: Dict[str, Any], profile: Dict[str, Any], skills: List[Dict[str, Any]], navigate_to: Callable[[str], None]) -> None:
    uid = user["id"]
    stats = get_individual_dashboard_stats(uid)

    # 1. Welcome Hero Banner
    _render_html(
        f"""
        <div style="background: linear-gradient(135deg, #2E1065 0%, #7C3AED 35%, #2563EB 75%, #06B6D4 100%); border-radius: 18px; border: 1.5px solid rgba(255, 255, 255, 0.25); padding: 2rem 2.4rem; color: #FFFFFF; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; box-shadow: 0 8px 30px rgba(124, 58, 237, 0.35); position: relative; overflow: hidden;">
            <div style="z-index: 2; max-width: 65%;">
                <div style="display: inline-flex; align-items: center; gap: 7px; background: rgba(255, 255, 255, 0.18); border: 1px solid rgba(255, 255, 255, 0.35); padding: 5px 14px; border-radius: 9999px; font-size: 0.76rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: #FDF4FF; margin-bottom: 10px;">
                    {_get_svg_icon("sparkles", size=13, color="#FEF08A")} Independent Professional Career Studio
                </div>
                <div style="font-size: 2.15rem; font-weight: 900; color: #FFFFFF; line-height: 1.2; margin-bottom: 8px; letter-spacing: -0.02em;">
                    Welcome back, {user.get('name', 'Professional')}
                </div>
                <div style="font-size: 1rem; color: rgba(255, 255, 255, 0.94); font-weight: 400; line-height: 1.55;">
                    Track personal competencies, validate your knowledge through standardized technical assessments, and navigate your independent career milestones.
                </div>
            </div>
            <div style="z-index: 2; flex-shrink: 0; text-align: right;">
                <div style="background: rgba(255, 255, 255, 0.16); border: 1.5px solid rgba(255, 255, 255, 0.3); border-radius: 16px; padding: 14px 22px; text-align: center; backdrop-filter: blur(8px); box-shadow: 0 6px 20px rgba(0,0,0,0.15);">
                    <div style="font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 800; color: #A5F3FC;">Target Role</div>
                    <div style="font-size: 1.3rem; font-weight: 900; color: #FFFFFF; margin-top: 3px;">{profile.get('target_role') or stats.get('target_role') or 'Full Stack Engineer'}</div>
                    <div style="font-size: 0.80rem; color: #FEF08A; font-weight: 800; margin-top: 3px;">{stats.get('match_percentage', stats.get('role_readiness', 0))}% Competency Readiness</div>
                </div>
            </div>
        </div>
        """
    )

    # 2. Four Solid Vibrant KPI Cards
    completed_cnt = stats.get('completed_assessments', 0)
    avg_score_val = stats.get('avg_assessment_score', stats.get('average_assessment_score', 0.0))
    avg_score_text = f"{avg_score_val}%" if completed_cnt > 0 else "N/A"
    avg_score_sub = "Across verified tests" if completed_cnt > 0 else "Take an assessment to verify"

    _render_html(
        f"""
        <div class="kpi-row-grid-vibrant" style="margin-bottom: 1.5rem;">
            <div class="kpi-card-vibrant kpi-vibrant-blue">
                <div class="kpi-vibrant-icon">
                    {_get_svg_icon("briefcase", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Total Skills Added</div>
                    <div class="kpi-vibrant-number">{stats.get('total_skills', 0)}</div>
                    <div class="kpi-vibrant-sub">
                        {_get_svg_icon("sparkles", size=13, color="#FFFFFF")} Self-reported portfolio
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-green">
                <div class="kpi-vibrant-icon">
                    {_get_svg_icon("award", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Completed Assessments</div>
                    <div class="kpi-vibrant-number">{stats.get('completed_assessments', 0)}</div>
                    <div class="kpi-vibrant-sub">
                        {_get_svg_icon("check", size=13, color="#FFFFFF")} Standardized MCQ evals
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-purple">
                <div class="kpi-vibrant-icon">
                    {_get_svg_icon("trending_up", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Average Assessment Score</div>
                    <div class="kpi-vibrant-number">{avg_score_text}</div>
                    <div class="kpi-vibrant-sub">
                        {_get_svg_icon("trending_up", size=13, color="#FFFFFF")} {avg_score_sub}
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-orange">
                <div class="kpi-vibrant-icon">
                    {_get_svg_icon("target", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Career Goals Progress</div>
                    <div class="kpi-vibrant-number">{stats.get('goal_avg_progress', stats.get('career_growth_progress', 0))}%</div>
                    <div class="kpi-vibrant-sub">
                        {_get_svg_icon("check", size=13, color="#FFFFFF")} {stats.get('completed_goals', 0)} / {stats.get('total_goals', 0)} milestones achieved
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # 3. Two Columns: Charts & Visualizations
    col_chart_left, col_chart_right = st.columns([1.1, 1.2], gap="medium")

    with col_chart_left:
        with st.container(border=True):
            st.markdown("<h3 style='font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;'>Skill Proficiency Breakdown</h3>", unsafe_allow_html=True)
            dist = stats.get("proficiency_distribution", {})
            if any(dist.values()):
                dist_df = pd.DataFrame([{"Proficiency": k, "Count": v} for k, v in dist.items()])
                color_map = {
                    "Beginner": "#A5B4FC",
                    "Intermediate": "#6366F1",
                    "Advanced": "#8B5CF6",
                    "Expert": "#4338CA"
                }
                fig_dist = px.bar(
                    dist_df, x="Proficiency", y="Count", color="Proficiency",
                    color_discrete_map=color_map,
                    text="Count"
                )
                fig_dist.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False, title=""),
                    yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Skills Count")
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("No skills recorded yet. Add your competencies in the Skills & Assessment module.")
                if st.button("Add Your First Skill", key="btn_dash_add_skill", type="primary"):
                    navigate_to("Skills & Assessment")

    with col_chart_right:
        with st.container(border=True):
            st.markdown("<h3 style='font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;'>Technical Assessment Performance</h3>", unsafe_allow_html=True)
            hist = stats.get("assessment_history", [])
            if hist:
                hist_df = pd.DataFrame(hist)
                if "skill_name" not in hist_df.columns:
                    hist_df["skill_name"] = hist_df.get("category", "Technical")
                else:
                    hist_df["skill_name"] = hist_df["skill_name"].fillna("Technical")

                fig_hist = px.bar(
                    hist_df, x="skill_name", y="score",
                    color="score",
                    color_continuous_scale=["#6366F1", "#8B5CF6", "#22D3EE"],
                    text="score",
                    labels={"skill_name": "Skill", "score": "Score (%)"}
                )
                fig_hist.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=False, title=""),
                    yaxis=dict(showgrid=True, gridcolor="#F1F5F9", range=[0, 100], title="Score (%)")
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No technical assessments completed yet. Take an assessment to evaluate your knowledge.")
                if st.button("Start a Technical Assessment", key="btn_dash_take_eval", type="primary"):
                    navigate_to("Skills & Assessment")

    # 4. Target Role Skill Gap Snapshot & Career Roadmap
    col_gap, col_act = st.columns([1.3, 1.0], gap="medium")

    with col_gap:
        with st.container(border=True):
            st.markdown(f"<h3 style='font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.35rem;'>Skill Gap Analysis Snapshot &bull; {profile.get('target_role') or stats.get('target_role') or 'Full Stack Engineer'}</h3>", unsafe_allow_html=True)
            st.caption("Self-reported skills are compared against role requirements. Assessments provide verified proficiency evidence.")

            gaps = stats.get("role_gaps", [])
            if gaps:
                gap_rows = []
                for g in gaps[:6]:
                    status_val = g.get('status') or ("Acquired" if g.get('priority') == "Met" else ("Needs Improvement" if g.get('priority') == "Medium" else "Missing Skill"))
                    status_badge = '<span style="background: #ECFDF5; color: #047857; font-weight: 700; border-radius: 9999px; padding: 2px 8px; font-size: 0.74rem;">Acquired</span>' if status_val == "Acquired" else (
                        '<span style="background: #FEF3C7; color: #B45309; font-weight: 700; border-radius: 9999px; padding: 2px 8px; font-size: 0.74rem;">Needs Improvement</span>' if status_val == "Needs Improvement" else
                        '<span style="background: #FEE2E2; color: #B91C1C; font-weight: 700; border-radius: 9999px; padding: 2px 8px; font-size: 0.74rem;">Missing Skill</span>'
                    )
                    evidence_badge = f'<span style="color: #2563EB; font-weight: 600; font-size: 0.78rem;">Score: {g["verified_score"]}%</span>' if g.get("verified_score") is not None else '<span style="color: #94A3B8; font-size: 0.74rem;">Self-Reported Only</span>'
                    curr_lvl = g.get('current_level', g.get('current', 0))
                    req_lvl = g.get('required_level', g.get('required', 0))
                    skill_name_disp = g.get('skill', 'Skill')

                    gap_rows.append(
                        f"""
                        <tr style="border-bottom: 1px solid #F1F5F9;">
                            <td style="padding: 9px 12px; font-weight: 700; color: #0F172A;">{skill_name_disp}</td>
                            <td style="padding: 9px 12px; font-size: 0.85rem; color: #475569;">Level {curr_lvl} / Req: {req_lvl}</td>
                            <td style="padding: 9px 12px;">{status_badge}</td>
                            <td style="padding: 9px 12px;">{evidence_badge}</td>
                        </tr>
                        """
                    )
                _render_html(
                    f"""
                    <div style="overflow-x: auto; margin-top: 8px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.86rem;">
                            <thead>
                                <tr style="background: #F8FAFC; border-bottom: 2px solid #E2E8F0; text-align: left; color: #64748B; font-size: 0.76rem; text-transform: uppercase;">
                                    <th style="padding: 8px 12px;">Required Competency</th>
                                    <th style="padding: 8px 12px;">Level Comparison</th>
                                    <th style="padding: 8px 12px;">Status</th>
                                    <th style="padding: 8px 12px;">Assessment Evidence</th>
                                </tr>
                            </thead>
                            <tbody>{''.join(gap_rows)}</tbody>
                        </table>
                    </div>
                    """
                )
                st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
                if st.button("Open Full Skill Gap Analysis", key="btn_dash_open_gap"):
                    navigate_to("Role Match & Gaps")
            else:
                st.info("Select a target role in your profile to run a personalized skill gap analysis.")

    with col_act:
        with st.container(border=True):
            st.markdown("<h3 style='font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 0.35rem;'>Recent Activities</h3>", unsafe_allow_html=True)
            activities = stats.get("recent_activities", [])
            if activities:
                act_items = []
                for act in activities[:5]:
                    act_type = str(act.get("type", "Activity")).capitalize()
                    type_color = "#2563EB" if act_type == "Skill" else ("#10B981" if act_type == "Assessment" else "#EA580C")
                    act_date = act.get('timestamp') or act.get('date', '')
                    act_items.append(
                        f"""
                        <div style="display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid #F1F5F9;">
                            <span style="font-size: 0.72rem; font-weight: 700; color: {type_color}; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 2px 6px; white-space: nowrap;">
                                {act_type.upper()}
                            </span>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: #0F172A; font-size: 0.86rem;">{act.get('title', '')}</div>
                                <div style="font-size: 0.76rem; color: #64748B;">{act_date}</div>
                            </div>
                        </div>
                        """
                    )
                _render_html(f"<div>{''.join(act_items)}</div>")
            else:
                st.write("No recent activities recorded. Start by adding skills or attempting assessments.")

    # 4. Career Development & Acceleration Launchpad
    _render_html(
        f"""
        <div style="margin-top: 1.5rem; margin-bottom: 0.6rem; font-size: 1.15rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 8px;">
            {_get_svg_icon("sparkles", size=20, color="#2563EB")} Career Growth &amp; AI Acceleration Tools
        </div>
        """
    )
    col_tl1, col_tl2, col_tl3 = st.columns(3)
    with col_tl1:
        with st.container(border=True):
            st.markdown(f"<div style='border-left: 4px solid #2563EB; padding-left: 8px;'><strong>{_get_svg_icon('reports', size=16, color='#2563EB')} ATS Resume Studio</strong></div>", unsafe_allow_html=True)
            st.caption("ATS-ready resume builder with STAR bullet rewrites and PDF export.")
            if st.button("Open Resume Studio", key="ind_dash_btn_resume", type="primary", use_container_width=True):
                navigate_to("Resume Studio")
    with col_tl2:
        with st.container(border=True):
            st.markdown(f"<div style='border-left: 4px solid #0D9488; padding-left: 8px;'><strong>{_get_svg_icon('target', size=16, color='#0D9488')} Career Direction</strong></div>", unsafe_allow_html=True)
            st.caption("Define your target industry, role benchmarks, and growth timeline.")
            if st.button("Set Career Direction", key="ind_dash_btn_direction", use_container_width=True):
                navigate_to("Career Direction")
    with col_tl3:
        with st.container(border=True):
            st.markdown(f"<div style='border-left: 4px solid #7C3AED; padding-left: 8px;'><strong>{_get_svg_icon('coach', size=16, color='#7C3AED')} AI Career Coach</strong></div>", unsafe_allow_html=True)
            st.caption("Executive strategy guidance evaluating gaps and role readiness.")
            if st.button("Ask Career Coach", key="ind_dash_btn_coach", use_container_width=True):
                navigate_to("Career Coach")

    # 5. Join an Organization Promotional Callout Banner
    _render_html(
        f"""
        <div style="margin-top: 1.5rem; background: #F8FAFC; border: 1.5px dashed #CBD5E1; border-radius: 14px; padding: 1.35rem 1.75rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div style="width: 44px; height: 44px; border-radius: 10px; background: #EFF6FF; border: 1px solid #DBEAFE; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {_get_svg_icon("building", size=22, color="#2563EB")}
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Joining an employer or organization?</div>
                    <div style="font-size: 0.85rem; color: #64748B;">Enter your HR-issued invitation code at any time. All your personal skills, assessment history, and career goals are seamlessly preserved.</div>
                </div>
            </div>
        </div>
        """
    )
    c_btn1, c_sp, c_btn2 = st.columns([1.5, 3.5, 1.5])
    with c_btn1:
        if st.button("Enter Invitation Code", key="btn_dash_join_org", type="secondary", use_container_width=True):
            navigate_to("Join an Organization")


# ==============================================================================
# SECTION 3C: PERSONAL SKILL MANAGEMENT MODULE
# ==============================================================================
def render_individual_skills(user: Dict[str, Any], skills: List[Dict[str, Any]], navigate_to: Callable[[str], None]) -> None:
    uid = user["id"]
    _render_html(
        f"""
        <div class="colorful-page-hero" style="background: linear-gradient(135deg, #FFFFFF 0%, #F0FDFA 60%, #EFF6FF 100%); border-left: 6px solid #0D9488;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="hero-icon-container" style="background: linear-gradient(135deg, #0D9488 0%, #2563EB 100%);">
                    {_get_svg_icon("briefcase", size=24, color="#FFFFFF")}
                </div>
                <div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                        Personal Skills Portfolio &amp; Inventory
                    </div>
                    <div style="color: #475569; font-size: 0.94rem; margin-top: 3px; font-weight: 500;">
                        Manage verified competencies, proficiency levels, and hands-on experience notes.
                    </div>
                </div>
            </div>
            <div>
                <span class="hero-badge-pill" style="background: linear-gradient(135deg, #0D9488, #2563EB);">
                    SKILL INVENTORY
                </span>
            </div>
        </div>
        """
    )

    # Top Add Skill Bar
    with st.expander("Add New Competency to Profile", expanded=(len(skills) == 0)):
        with st.form("form_add_individual_skill"):
            c_s1, c_s2 = st.columns(2)
            skill_name = c_s1.text_input("Skill Name *", placeholder="e.g. Python, Docker, React.js, SQL")
            category = c_s2.selectbox("Skill Category", ["Technical", "Soft Skills", "Domain & Leadership", "Cloud & DevOps"])

            c_s3, c_s4 = st.columns(2)
            prof_level = c_s3.selectbox("Proficiency Level *", ["Beginner", "Intermediate", "Advanced", "Expert"], index=1)
            years_exp = c_s4.number_input("Years of Practical Experience", min_value=0.0, max_value=50.0, value=1.0, step=0.5)

            desc = st.text_area("Practical Experience & Project Application Notes (Optional)", placeholder="Summarize hands-on projects, tools, frameworks, and practical experience with this skill.")
            submit_skill = st.form_submit_button("Add Skill to Portfolio", type="primary", use_container_width=True)

            if submit_skill:
                ok, msg = add_skill(uid, skill_name, category, prof_level, years_exp, description=desc)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # Skills List & Management
    st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 800; color: #0F172A; margin-top: 1.5rem; margin-bottom: 0.85rem;'>Your Skills Portfolio ({len(skills)})</h3>", unsafe_allow_html=True)

    if not skills:
        st.info("You haven't added any skills to your profile yet. Use the form above to add your core competencies.")
        return

    # Filter by category
    categories = ["All Categories"] + sorted(list({s.get("category", "Technical") for s in skills}))
    sel_cat = st.selectbox("Filter Skills by Category", categories, key="filter_skill_cat")

    filtered_skills = skills if sel_cat == "All Categories" else [s for s in skills if s.get("category") == sel_cat]

    for sk in filtered_skills:
        with st.container(border=True):
            col_info, col_actions = st.columns([3.5, 1.5])
            with col_info:
                prof = sk.get("proficiency", "Intermediate")
                badge_bg = "#EEF2FF" if prof == "Intermediate" else ("#ECFDF5" if prof in ["Advanced", "Expert"] else "#F1F5F9")
                badge_col = "#4F46E5" if prof == "Intermediate" else ("#059669" if prof in ["Advanced", "Expert"] else "#64748B")

                _render_html(
                    f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: #0F172A;">{sk['name']}</span>
                        <span style="background: {badge_bg}; color: {badge_col}; border: 1px solid {badge_col}33; padding: 2px 9px; border-radius: 9999px; font-size: 0.74rem; font-weight: 700;">{prof}</span>
                        <span style="background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; padding: 2px 8px; border-radius: 6px; font-size: 0.72rem;">{sk.get('category', 'Technical')}</span>
                    </div>
                    <div style="font-size: 0.84rem; color: #64748B; margin-bottom: 4px;">
                        <strong>{sk.get('years', 0.0)} years</strong> experience
                    </div>
                    """
                )
                if sk.get("description"):
                    st.markdown(f"<div style='font-size: 0.84rem; color: #334155; line-height: 1.4; background: #F8FAFC; padding: 8px 12px; border-radius: 6px; border: 1px solid #E2E8F0;'>{sk['description']}</div>", unsafe_allow_html=True)

            with col_actions:
                c_edit, c_del = st.columns(2)
                with c_edit:
                    with st.popover("Edit"):
                        st.markdown(f"**Edit {sk['name']}**")
                        prof_choices = ["Beginner", "Intermediate", "Advanced", "Expert"]
                        p_idx = prof_choices.index(prof) if prof in prof_choices else 1
                        edit_prof = st.selectbox("Proficiency", prof_choices, index=p_idx, key=f"edit_prof_{sk['id']}")
                        edit_years = st.number_input("Years", min_value=0.0, max_value=50.0, value=float(sk.get("years", 1.0)), step=0.5, key=f"edit_yrs_{sk['id']}")
                        edit_desc = st.text_area("Practical Notes", value=sk.get("description", ""), key=f"edit_desc_{sk['id']}")
                        if st.button("Save Changes", key=f"save_sk_{sk['id']}", type="primary"):
                            ok_up, msg_up = update_skill(uid, sk["id"], edit_prof, edit_years, description=edit_desc)
                            if ok_up:
                                st.success("Updated!")
                                st.rerun()
                            else:
                                st.error(msg_up)
                with c_del:
                    if st.button("Delete", key=f"del_sk_{sk['id']}", type="secondary"):
                        delete_skill(uid, sk["id"])
                        st.success(f"Removed '{sk['name']}'.")
                        st.rerun()


# ==============================================================================
# SECTION 3D: SKILL ASSESSMENT MODULE (MCQ TESTS, RESULTS, EXPLANATIONS, HISTORY)
# ==============================================================================
def render_individual_assessments(user: Dict[str, Any], skills: List[Dict[str, Any]]) -> None:
    uid = user["id"]
    _render_html(
        f"""
        <div class="colorful-page-hero" style="background: linear-gradient(135deg, #FFFFFF 0%, #FAF5FF 60%, #EFF6FF 100%); border-left: 6px solid #7C3AED;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="hero-icon-container" style="background: linear-gradient(135deg, #7C3AED 0%, #2563EB 100%);">
                    {_get_svg_icon("check", size=24, color="#FFFFFF")}
                </div>
                <div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                        Standardized Technical MCQ Assessments
                    </div>
                    <div style="color: #475569; font-size: 0.94rem; margin-top: 3px; font-weight: 500;">
                        Validate competencies with automated evaluation, instant scoring, and concept feedback.
                    </div>
                </div>
            </div>
            <div>
                <span class="hero-badge-pill" style="background: linear-gradient(135deg, #7C3AED, #2563EB);">
                    TESTING ENGINE
                </span>
            </div>
        </div>
        """
    )

    catalog = get_available_assessments()

    tab_test, tab_history = st.tabs(["Take Assessment", "Assessment History & Score Tracking"])

    with tab_test:
        if not catalog:
            st.info("No assessments currently available.")
            return

        skill_options = [c.get("skill") or c.get("skill_name") for c in catalog]
        sel_skill = st.selectbox(
            "Select Skill to Evaluate *",
            options=skill_options,
            format_func=lambda x: f"{x} ({next((c.get('question_count') or c.get('total_questions', 5) for c in catalog if (c.get('skill') == x or c.get('skill_name') == x)), 5)} Questions Available)"
        )

        st.markdown(f"<div style='margin: 1rem 0; padding: 12px 18px; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; font-size: 0.88rem; color: #1E40AF;'>You are attempting the standardized <strong>{sel_skill} Competency Assessment</strong>. Select the best answer for each question and submit for immediate automated scoring and concept feedback.</div>", unsafe_allow_html=True)

        questions = get_assessment_questions(sel_skill)

        with st.form(f"assessment_form_{sel_skill}"):
            user_answers: Dict[str, Any] = {}
            for idx, q in enumerate(questions, start=1):
                st.markdown(f"<div style='font-weight: 700; color: #0F172A; font-size: 1rem; margin-top: 1rem; margin-bottom: 0.5rem;'>Question {idx}: {q.get('question', '')}</div>", unsafe_allow_html=True)
                opts = q.get("options", [])
                choice = st.radio(
                    f"Q{idx} Options",
                    options=list(range(len(opts))),
                    format_func=lambda i, options_list=opts: options_list[i] if 0 <= i < len(options_list) else "",
                    key=f"q_{sel_skill}_{q['id']}",
                    label_visibility="collapsed"
                )
                user_answers[q["id"]] = opts[choice] if (0 <= choice < len(opts)) else ""

            submit_eval = st.form_submit_button("Submit Assessment for Evaluation", type="primary", use_container_width=True)

            if submit_eval:
                result = evaluate_assessment(uid, sel_skill, user_answers)
                st.session_state[f"last_assessment_result_{sel_skill}"] = result

        # Show Results if available
        last_res = st.session_state.get(f"last_assessment_result_{sel_skill}")
        if last_res:
            score_pct = last_res.get("score_percentage", 0.0)
            banner_bg = "#ECFDF5" if score_pct >= 80 else ("#EFF6FF" if score_pct >= 60 else "#FEF2F2")
            banner_border = "#10B981" if score_pct >= 80 else ("#3B82F6" if score_pct >= 60 else "#EF4444")
            banner_color = "#047857" if score_pct >= 80 else ("#1D4ED8" if score_pct >= 60 else "#B91C1C")
            c_cnt = last_res.get("correct_count", last_res.get("correct_answers", 0))
            t_cnt = last_res.get("total_questions", len(questions))
            p_rat = last_res.get("proficiency_rating", "Proficient" if score_pct >= 70 else "Developing")

            _render_html(
                f"""
                <div style="margin-top: 1.5rem; background: {banner_bg}; border: 2px solid {banner_border}; border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: {banner_color};">Assessment Results &bull; {last_res.get('skill_name', sel_skill)}</div>
                    <div style="font-size: 2.5rem; font-weight: 800; color: {banner_color}; margin: 4px 0;">{score_pct}% Score</div>
                    <div style="font-size: 1rem; font-weight: 600; color: #1E293B;">
                        {c_cnt} of {t_cnt} questions correct &bull; Rating: <strong>{p_rat}</strong>
                    </div>
                    <div style="font-size: 0.85rem; color: #475569; margin-top: 6px;">
                        This verified assessment score has been permanently recorded in your personal career profile.
                    </div>
                </div>
                """
            )

            st.markdown("<h3 style='font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-top: 1.25rem; margin-bottom: 0.5rem;'>Detailed Answer Breakdown & Explanations</h3>", unsafe_allow_html=True)
            for idx, item in enumerate(last_res["breakdown"], start=1):
                is_correct = item["is_correct"]
                card_bg = "#F0FDF4" if is_correct else "#FEF2F2"
                card_border = "#BBF7D0" if is_correct else "#FECACA"
                icon_tag = _get_svg_icon("check", size=18, color="#10B981") if is_correct else _get_svg_icon("cross", size=18, color="#EF4444")

                _render_html(
                    f"""
                    <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 10px; padding: 12px 16px; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #0F172A; font-size: 0.95rem; margin-bottom: 6px;">
                            {icon_tag} Question {idx}: {item['question']}
                        </div>
                        <div style="font-size: 0.86rem; color: #334155; margin-left: 26px; line-height: 1.5;">
                            <div>Your Answer: <strong>{item['user_answer']}</strong> {'(Correct)' if is_correct else '(Incorrect)'}</div>
                            {f"<div style='color: #047857;'>Correct Answer: <strong>{item['correct_answer']}</strong></div>" if not is_correct else ""}
                            <div style="margin-top: 4px; font-size: 0.82rem; color: #475569; background: rgba(255,255,255,0.7); padding: 6px 10px; border-radius: 6px;">
                                <strong>Explanation:</strong> {item['explanation']}
                            </div>
                        </div>
                    </div>
                    """
                )

    with tab_history:
        st.markdown("<h3 style='font-size: 1.25rem; font-weight: 800; color: #0F172A; margin-bottom: 0.5rem;'>Assessment History & Score Progression</h3>", unsafe_allow_html=True)
        hist = get_skill_assessment_history(uid)
        if hist:
            hist_df = pd.DataFrame(hist)
            # Display history table
            rows = []
            for h in hist:
                d_val = h.get("score_delta", h.get("delta"))
                delta_str = f"+{d_val}%" if d_val is not None and d_val > 0 else (
                    f"{d_val}%" if d_val is not None and d_val < 0 else "Baseline"
                )
                delta_color = "#10B981" if "+" in delta_str else ("#EF4444" if "-" in delta_str else "#64748B")

                rows.append(
                    f"""
                    <tr style="border-bottom: 1px solid #F1F5F9;">
                        <td style="padding: 10px 14px; font-weight: 700; color: #0F172A;">{h.get('skill_name', 'Skill')}</td>
                        <td style="padding: 10px 14px; font-weight: 800; color: #2563EB;">{h.get('score', 0)}%</td>
                        <td style="padding: 10px 14px; font-weight: 700; color: {delta_color};">{delta_str}</td>
                        <td style="padding: 10px 14px; color: #64748B; font-size: 0.82rem;">{h.get('created_at', '')}</td>
                        <td style="padding: 10px 14px; font-size: 0.82rem; color: #475569;">{h.get('notes', '')}</td>
                    </tr>
                    """
                )
            _render_html(
                f"""
                <div style="overflow-x: auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.88rem;">
                        <thead>
                            <tr style="background: #F8FAFC; border-bottom: 2px solid #E2E8F0; text-align: left; color: #64748B; font-size: 0.76rem; text-transform: uppercase;">
                                <th style="padding: 10px 14px;">Evaluated Skill</th>
                                <th style="padding: 10px 14px;">Score</th>
                                <th style="padding: 10px 14px;">Improvement Delta</th>
                                <th style="padding: 10px 14px;">Date Completed</th>
                                <th style="padding: 10px 14px;">Performance Rating</th>
                            </tr>
                        </thead>
                        <tbody>{''.join(rows)}</tbody>
                    </table>
                </div>
                """
            )
        else:
            st.info("No assessment history found yet. Complete a test above to begin building your verified score record.")


# ==============================================================================
# SECTION 3E: PERSONAL SKILL GAP ANALYSIS
# ==============================================================================
def render_individual_skill_gaps(user: Dict[str, Any], skills: List[Dict[str, Any]]) -> None:
    uid = user["id"]
    profile = get_profile(uid)

    _render_html(
        f"""
        <div class="colorful-page-hero" style="background: linear-gradient(135deg, #FFFFFF 0%, #F5F3FF 60%, #FDF2F8 100%); border-left: 6px solid #8B5CF6;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="hero-icon-container" style="background: linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%);">
                    {_get_svg_icon("target", size=24, color="#FFFFFF")}
                </div>
                <div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                        Benchmark Skill Gap Analysis
                    </div>
                    <div style="color: #475569; font-size: 0.94rem; margin-top: 3px; font-weight: 500;">
                        Compare profile competencies against target roles to identify shortfalls and plan development.
                    </div>
                </div>
            </div>
            <div>
                <span class="hero-badge-pill" style="background: linear-gradient(135deg, #8B5CF6, #EC4899);">
                    GAP TELEMETRY
                </span>
            </div>
        </div>
        """
    )

    roles_list = list(ROLE_CATALOG.keys())
    default_role = profile.get("target_role") or "Junior Python Developer"
    default_idx = roles_list.index(default_role) if default_role in roles_list else 0

    target_role = st.selectbox("Target Career / Job Role *", roles_list, index=default_idx)

    role_info = ROLE_CATALOG[target_role]
    required_skills = role_info["skills"]

    # Pull user skills map & assessment map
    user_skills_map = {s["name"].strip().lower(): LEVELS.get(s["proficiency"], 1) for s in skills}
    assessments = get_assessments(uid)
    assessment_map: Dict[str, float] = {}
    for a in assessments:
        sk_n = a.get("skill_name", "").strip().lower()
        if sk_n:
            assessment_map[sk_n] = max(assessment_map.get(sk_n, 0.0), float(a.get("score", 0.0)))

    # Compare
    acquired = []
    improving = []
    missing = []

    for req_name, req_lvl in required_skills.items():
        curr_lvl = user_skills_map.get(req_name.strip().lower(), 0)
        verified_score = assessment_map.get(req_name.strip().lower())

        item = {
            "skill": req_name,
            "required_level": req_lvl,
            "current_level": curr_lvl,
            "gap": max(0, req_lvl - curr_lvl),
            "verified_score": verified_score
        }

        if curr_lvl >= req_lvl:
            acquired.append(item)
        elif curr_lvl > 0:
            improving.append(item)
        else:
            missing.append(item)

    total_req = len(required_skills)
    match_pct = round(((len(acquired) + 0.5 * len(improving)) / max(1, total_req)) * 100)

    # Readiness Banner
    _render_html(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.75rem; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div>
                <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: #64748B;">Role Readiness Index</div>
                <div style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 2px 0;">{match_pct}% Match for {target_role}</div>
                <div style="font-size: 0.86rem; color: #64748B;">
                    <strong>{len(acquired)}</strong> Acquired &bull; <strong>{len(improving)}</strong> Need Improvement &bull; <strong>{len(missing)}</strong> Missing
                </div>
            </div>
            <div style="display: flex; gap: 8px;">
                <span style="background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; font-weight: 700; font-size: 0.8rem; padding: 6px 12px; border-radius: 8px;">
                    Acquired: {len(acquired)}
                </span>
                <span style="background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; font-weight: 700; font-size: 0.8rem; padding: 6px 12px; border-radius: 8px;">
                    Improving: {len(improving)}
                </span>
                <span style="background: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; font-weight: 700; font-size: 0.8rem; padding: 6px 12px; border-radius: 8px;">
                    Missing: {len(missing)}
                </span>
            </div>
        </div>
        """
    )

    # 3 Category Tabs
    tab_acq, tab_imp, tab_mis, tab_rec = st.tabs([
        f"Skills Already Acquired ({len(acquired)})",
        f"Skills Requiring Improvement ({len(improving)})",
        f"Missing Skills ({len(missing)})",
        "Recommended Learning Priorities"
    ])

    with tab_acq:
        if acquired:
            for item in acquired:
                ev_str = f"Verified: {item['verified_score']}%" if item["verified_score"] is not None else "Self-reported (No Assessment Taken Yet)"
                _render_html(
                    f"""
                    <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-weight: 800; font-size: 1.05rem; color: #065F46;">{item['skill']}</div>
                            <div style="font-size: 0.82rem; color: #047857;">Current Level {item['current_level']} meets or exceeds Required Level {item['required_level']}</div>
                        </div>
                        <span style="font-size: 0.78rem; font-weight: 700; background: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 9999px;">{ev_str}</span>
                    </div>
                    """
                )
        else:
            st.info("No acquired skills meet the benchmark for this role yet.")

    with tab_imp:
        if improving:
            for item in improving:
                ev_str = f"Verified: {item['verified_score']}%" if item["verified_score"] is not None else "Self-reported"
                _render_html(
                    f"""
                    <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-weight: 800; font-size: 1.05rem; color: #92400E;">{item['skill']}</div>
                            <div style="font-size: 0.82rem; color: #B45309;">Current: Level {item['current_level']} &rarr; Target: Level {item['required_level']} (Shortfall: {item['gap']} levels)</div>
                        </div>
                        <span style="font-size: 0.78rem; font-weight: 700; background: #FEF3C7; color: #B45309; padding: 4px 10px; border-radius: 9999px;">{ev_str}</span>
                    </div>
                    """
                )
        else:
            st.success("No partial skills requiring improvement!")

    with tab_mis:
        if missing:
            for item in missing:
                _render_html(
                    f"""
                    <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-weight: 800; font-size: 1.05rem; color: #991B1B;">{item['skill']}</div>
                            <div style="font-size: 0.82rem; color: #B91C1C;">Not yet added to your profile &bull; Required Target Level: {item['required_level']}</div>
                        </div>
                        <span style="font-size: 0.78rem; font-weight: 700; background: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 9999px;">Priority Addition</span>
                    </div>
                    """
                )
        else:
            st.success("Great job! No required skills are completely missing from your profile.")

    with tab_rec:
        st.markdown(f"**Recommended Curriculum for {target_role}:**")
        recs = role_info.get("recommended_training", [])
        for r in recs:
            st.markdown(f"- 📘 **{r}**")
        st.markdown(f"**Criteria Note:** {role_info.get('criteria', '')}")


# ==============================================================================
# SECTION 3F: CAREER GOAL MANAGEMENT
# ==============================================================================
def render_individual_career_goals(user: Dict[str, Any], navigate_to: Callable[[str], None]) -> None:
    uid = user["id"]
    _render_html(
        f"""
        <div class="colorful-page-hero" style="background: linear-gradient(135deg, #FFFFFF 0%, #FFF7ED 60%, #FEF2F2 100%); border-left: 6px solid #F97316;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="hero-icon-container" style="background: linear-gradient(135deg, #F97316 0%, #F43F5E 100%);">
                    {_get_svg_icon("award", size=24, color="#FFFFFF")}
                </div>
                <div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                        Personal Career Milestones &amp; SMART Goals
                    </div>
                    <div style="color: #475569; font-size: 0.94rem; margin-top: 3px; font-weight: 500;">
                        Define target designations, completion timelines, and monitor developmental sprints.
                    </div>
                </div>
            </div>
            <div>
                <span class="hero-badge-pill" style="background: linear-gradient(135deg, #F97316, #F43F5E);">
                    GOAL TRACKER
                </span>
            </div>
        </div>
        """
    )

    # Create Goal Form
    with st.expander("Create New Career Goal", expanded=False):
        with st.form("form_create_personal_goal"):
            c_g1, c_g2 = st.columns(2)
            title = c_g1.text_input("Goal Title *", placeholder="e.g. Master AWS Solutions Architect or Complete React Portfolio")
            target_desig = c_g2.text_input("Target Career Role / Project (Optional)", placeholder="e.g. Senior Software Engineer")

            c_g3, c_g4 = st.columns(2)
            target_date = c_g3.date_input("Target Completion Date *", value=date.today())
            initial_prog = c_g4.selectbox("Current Progress (%)", [0, 25, 50, 75, 100], index=0)

            desc = st.text_area("Milestone Description & Action Plan", placeholder="Outline specific action steps, study resources, and deliverables needed to achieve this goal.")
            submit_goal = st.form_submit_button("Create Career Goal", type="primary", use_container_width=True)

            if submit_goal:
                ok, msg = add_goal(
                    user_id=uid,
                    title=title,
                    description=desc,
                    target_date=str(target_date),
                    progress=initial_prog,
                    target_designation=target_desig
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # List Goals
    goals = get_goals(user_id=uid)
    stats = get_goal_stats(user_id=uid)

    # 4 Quick Metric Pills
    _render_html(
        f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 1.25rem 0;">
            <div style="background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #2563EB;">Total Goals</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #1E40AF;">{stats.get('total', 0)}</div>
            </div>
            <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #059669;">Completed</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #065F46;">{stats.get('completed', 0)}</div>
            </div>
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #D97706;">In Progress</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #92400E;">{stats.get('in_progress', 0)}</div>
            </div>
            <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #DC2626;">Overdue</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: #991B1B;">{stats.get('overdue', 0)}</div>
            </div>
        </div>
        """
    )

    if not goals:
        st.info("No active career goals recorded. Use the form above to add your first milestone.")
        return

    for g in goals:
        with st.container(border=True):
            col_main, col_ctl = st.columns([3.2, 1.8])
            with col_main:
                prog = int(g.get("progress") or 0)
                status = g.get("status", "In Progress")
                status_color = "#10B981" if status == "Completed" else ("#F59E0B" if status == "In Progress" else "#EF4444")
                g_title = g.get('title', 'Milestone')

                _render_html(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: #0F172A;">{g_title}</span>
                        <span style="background: {status_color}1A; color: {status_color}; border: 1px solid {status_color}4D; padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 700;">{status}</span>
                        {f"<span style='background: #F1F5F9; color: #475569; padding: 2px 7px; border-radius: 6px; font-size: 0.72rem;'>{g['target_designation']}</span>" if g.get('target_designation') else ""}
                    </div>
                    <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 6px;">
                        Target Completion: <strong>{g.get('target_date', 'Ongoing')}</strong>
                    </div>
                    """
                )
                if g.get("description"):
                    st.markdown(f"<div style='font-size: 0.84rem; color: #334155; line-height: 1.4; margin-bottom: 8px;'>{g['description']}</div>", unsafe_allow_html=True)

                st.progress(prog / 100)

            with col_ctl:
                st.markdown(f"<div style='font-size: 0.78rem; font-weight: 700; color: #64748B; margin-bottom: 4px;'>Update Progress: {prog}%</div>", unsafe_allow_html=True)
                c_p1, c_p2, c_p3 = st.columns(3)
                if c_p1.button("25%", key=f"prog_25_{g['id']}", disabled=(prog == 25)):
                    update_goal_progress(g["id"], uid, 25)
                    st.rerun()
                if c_p2.button("50%", key=f"prog_50_{g['id']}", disabled=(prog == 50)):
                    update_goal_progress(g["id"], uid, 50)
                    st.rerun()
                if c_p3.button("100%", key=f"prog_100_{g['id']}", disabled=(prog == 100), type="primary"):
                    update_goal_progress(g["id"], uid, 100)
                    st.rerun()

                st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                if st.button("Delete Goal", key=f"del_goal_{g['id']}", type="secondary"):
                    delete_goal(g["id"], uid)
                    st.rerun()


# ==============================================================================
# SECTION 3G: PERSONAL PERFORMANCE TRACKING & PROGRESS
# ==============================================================================
def render_individual_progress(user: Dict[str, Any]) -> None:
    uid = user["id"]
    stats = get_individual_dashboard_stats(uid)

    _render_html(
        f"""
        <div class="colorful-page-hero" style="background: linear-gradient(135deg, #FFFFFF 0%, #EEF2FF 60%, #F0F9FF 100%); border-left: 6px solid #2563EB;">
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="hero-icon-container" style="background: linear-gradient(135deg, #2563EB 0%, #06B6D4 100%);">
                    {_get_svg_icon("trending_up", size=24, color="#FFFFFF")}
                </div>
                <div>
                    <div style="font-size: 1.65rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">
                        Assessment Trajectory &amp; Growth Analytics
                    </div>
                    <div style="color: #475569; font-size: 0.94rem; margin-top: 3px; font-weight: 500;">
                        Track score improvements across test attempts and competency growth velocity over time.
                    </div>
                </div>
            </div>
            <div>
                <span class="hero-badge-pill" style="background: linear-gradient(135deg, #2563EB, #06B6D4);">
                    GROWTH ANALYTICS
                </span>
            </div>
        </div>
        """
    )

    hist = stats.get("assessment_history", [])

    if hist:
        # Score Trajectory Plot
        hist_df = pd.DataFrame(hist)
        if "skill_name" not in hist_df.columns:
            hist_df["skill_name"] = hist_df.get("category", "Technical")
        else:
            hist_df["skill_name"] = hist_df["skill_name"].fillna("Technical")
        hist_df["attempt"] = range(1, len(hist_df) + 1)

        fig_traj = px.line(
            hist_df, x="attempt", y="score",
            color="skill_name",
            markers=True,
            title="Technical Assessment Score Trajectory Across Attempts",
            labels={"attempt": "Assessment Attempt #", "score": "Score (%)", "skill_name": "Skill"}
        )
        fig_traj.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(range=[0, 100], gridcolor="#F1F5F9")
        )
        st.plotly_chart(fig_traj, use_container_width=True)
    else:
        st.info("No completed assessments to chart yet. Complete technical assessments to track improvement curves over time.")

    # Growth Metrics Summary Cards
    _render_html(
        f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 1.5rem;">
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: #64748B;">Competency Growth</div>
                <div style="font-size: 1.75rem; font-weight: 800; color: #0F172A; margin: 4px 0;">{stats.get('total_skills', 0)} Skills</div>
                <div style="font-size: 0.82rem; color: #10B981;">Added across portfolio</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: #64748B;">Verified Tests</div>
                <div style="font-size: 1.75rem; font-weight: 800; color: #0F172A; margin: 4px 0;">{stats.get('completed_assessments', 0)} Tests</div>
                <div style="font-size: 0.82rem; color: #2563EB;">Average Score: {stats.get('avg_assessment_score', stats.get('average_assessment_score', 0.0))}%</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: #64748B;">Milestones Achieved</div>
                <div style="font-size: 1.75rem; font-weight: 800; color: #0F172A; margin: 4px 0;">{stats.get('completed_goals', 0)} Goals</div>
                <div style="font-size: 0.82rem; color: #EA580C;">{stats.get('goal_avg_progress', stats.get('career_growth_progress', 0))}% Overall Completion</div>
            </div>
        </div>
        """
    )


# ==============================================================================
# SECTION 5: JOIN AN ORGANIZATION LATER
# ==============================================================================
def render_join_organization_card(user: Dict[str, Any]) -> None:
    uid = user["id"]
    st.markdown("<h1 style='font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin-bottom: 0.35rem;'>Join an Organization</h1>", unsafe_allow_html=True)
    st.caption("Seamlessly transition your individual professional account into an employer's corporate workspace while keeping all your skills, assessments, and goals intact.")

    with st.container(border=True):
        _render_html(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #EFF6FF; border: 1px solid #DBEAFE; display: flex; align-items: center; justify-content: center;">
                        {_get_svg_icon("building", size=22, color="#2563EB")}
                    </div>
                    <div>
                        <div style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">Employer Invitation Verification</div>
                        <div style="font-size: 0.85rem; color: #64748B;">Enter the official invitation code provided by your organization's HR administrator.</div>
                    </div>
                </div>
            </div>
            """
        )

        with st.form("form_join_org"):
            code_input = st.text_input("Organization Invitation Code *", placeholder="e.g. INV-TALENT-XXXX-YYYY").strip()
            submit_join = st.form_submit_button("Verify Code & Join Organization", type="primary", use_container_width=True)

            if submit_join:
                if not code_input:
                    st.error("Please enter a valid invitation code.")
                else:
                    join_res = join_organization(uid, code_input)
                    if isinstance(join_res, tuple) and len(join_res) == 3:
                        ok, msg, updated_user = join_res
                    elif isinstance(join_res, tuple) and len(join_res) == 2:
                        ok, msg = join_res
                        updated_user = None
                    else:
                        ok, msg, updated_user = False, "Unknown response", None

                    if ok:
                        if updated_user:
                            st.session_state.user["account_type"] = "Organization"
                            st.session_state.user["org_id"] = updated_user.get("org_id")
                            st.session_state.user["org_name"] = updated_user.get("org_name")
                            st.session_state.user["employee_id"] = updated_user.get("employee_id")
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg if isinstance(msg, str) else "Unable to join organization.")

        _render_html(
            """
            <div style="margin-top: 1.25rem; background: #F8FAFC; border-radius: 8px; padding: 12px 16px; font-size: 0.82rem; color: #64748B; line-height: 1.5;">
                <strong>Enterprise Data Retention Guarantee:</strong><br/>
                &bull; Your user account email, password, and credentials remain unchanged.<br/>
                &bull; All existing personal skills are automatically copied into the company employee skills directory.<br/>
                &bull; Past technical assessment scores and career goals are preserved and linked to your corporate profile.
            </div>
            """
        )
