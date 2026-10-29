from __future__ import annotations
import sys
import os
from pathlib import Path

# Guarantee application root directory is on sys.path and is current working directory
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    os.chdir(str(_ROOT))
except Exception:
    pass

from typing import Any, Dict, List, Optional, Tuple, Union
import json
import textwrap
import base64
from io import BytesIO
from datetime import datetime, date
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document

from services.core import (
    BASE_DIR, ROLE_CATALOG, LEVELS, STANDARD_DEPARTMENTS, EMPLOYMENT_STATUSES,
    init_db, register, login, get_user_by_id,
    create_organization, get_organization, list_organizations, get_organization_by_name, generate_unique_org_id,
    verify_and_activate_hr_admin,
    get_profile, save_profile, list_skills, add_skill, delete_skill,
    add_assessment, get_assessments, save_progress, get_progress,
    profile_completion, gap_analysis, recommendations, profile_analysis,
    role_match, export_user_data,
    add_employee, get_employees, get_employee_by_id, update_employee, delete_employee, get_all_departments,
    bulk_import_employees_df, get_sample_employee_csv,
    add_performance_review, get_performance_reviews, get_department_performance_summary,
    add_employee_skill, get_employee_skills, delete_employee_skill, get_employee_skill_gaps,
    add_goal, get_goals, get_goal_by_id, update_goal, update_goal_progress, delete_goal, get_goal_stats,
    add_training_record, get_training_records,
    get_org_dashboard_stats, get_employee_dashboard_data,
    get_db_path, check_db_health,
    get_resume, save_resume, import_skills_to_resume, format_resume_as_text, generate_resume_pdf,
    validate_url, validate_date_range
)
from services.reports import create_report
from services.ai_coach import (
    generate_ai_coaching_guidance,
    analyze_resume_with_ai,
    get_gemini_api_key
)
from style import load_css

# Vercel serverless entrypoint compatibility
def handler(environ=None, start_response=None):
    if start_response:
        start_response('200 OK', [('Content-Type', 'text/html')])
    return [b"OK"]

app = handler
application = handler

load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="Talent Growth — Talent Management Platform",
    page_icon="assets/talent_growth_icon_thumb.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema and ensure migrations (cached once per application lifecycle)
@st.cache_resource(show_spinner="Initializing Talent Growth database...")
def ensure_database_ready() -> bool:
    init_db()
    return True

ensure_database_ready()

@st.cache_data
def get_logo_b64(which: str = "icon") -> str:
    path = "assets/talent_growth_icon_thumb.png" if which == "icon" else "assets/talent_growth_full_thumb.png"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

@st.cache_data
def get_career_growth_illustration_b64() -> str:
    path = "assets/career_growth_transparent.png"
    if not os.path.exists(path):
        path = "assets/career_growth_clean.png"
    if not os.path.exists(path):
        path = "assets/career_growth_illustration.png"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

def render_html(html_str: str) -> None:
    """Directly renders pure HTML without markdown parser converting indented lines into code blocks."""
    clean_html = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean_html, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# CLEAN SVG ICON SYSTEM (Zero Emojis, Crisp Vector Icons via Data URIs)
# ------------------------------------------------------------------------------
_SVG_RAW_PATHS = {
    "dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "employees": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "performance": '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "skills": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "goals": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "reports": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "building": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "arrow_right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow_left": '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "user_check": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>',
    "profile": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "coach": '<path d="M12 2a8 8 0 0 0-8 8c0 3 1.5 5.5 4 6.8V19a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.2c2.5-1.3 4-3.8 4-6.8a8 8 0 0 0-8-8z"/><path d="M9 22h6"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "user_plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.9a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "analytics": '<line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "table": '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    "card": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "clipboard": '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "cloud": '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
    "trending_up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "lightbulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "key": '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "phone": '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "briefcase": '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "chevron_down": '<polyline points="6 9 12 15 18 9"/>',
    "external_link": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>'
}

@st.cache_data
def _build_svg_data_uri(inner_svg: str, width: int, height: int, stroke_color: str, fill_color: str) -> str:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_svg}</svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")

def get_svg_icon(name: str, size: int = 18, color: str = "#2563EB", extra_style: str = "") -> str:
    """Returns an inline, standalone, crisp SVG vector icon as a data URI img (NEVER stripped by sanitizers)."""
    if name == "brand_logo":
        icon_b64 = get_logo_b64("icon")
        return f'<img src="data:image/png;base64,{icon_b64}" style="width: {size}px; height: {size}px; border-radius: 8px; object-fit: contain; vertical-align: middle; {extra_style}" alt="Talent Growth Logo" />'
    elif name == "brand_full":
        full_b64 = get_logo_b64("full")
        return f'<img src="data:image/png;base64,{full_b64}" style="height: {size}px; max-width: 100%; object-fit: contain; vertical-align: middle; {extra_style}" alt="Talent Growth Logo" />'

    inner = _SVG_RAW_PATHS.get(name)
    if not inner:
        return f'<span style="display:inline-block; width:{size}px; height:{size}px; {extra_style}"></span>'

    stroke_color = color if (color and color != "currentColor") else "#334155"
    fill_color = stroke_color if name == "star" else "none"
    uri = _build_svg_data_uri(inner, size, size, stroke_color, fill_color)
    return f'<img src="{uri}" width="{size}" height="{size}" style="display: inline-block; vertical-align: middle; border: none; {extra_style}" alt="{name}" />'

# ------------------------------------------------------------------------------
# MODERN CORPORATE DESIGN SYSTEM & TOKENS (TalentManager / TalentPro Theme)
# ------------------------------------------------------------------------------
load_css()

# ------------------------------------------------------------------------------
# TABLE COLORATION & BADGE UTILITIES
# ------------------------------------------------------------------------------
def get_dept_badge_html(department: str) -> str:
    dept = (department or "").lower()
    if any(k in dept for k in ["eng", "dev", "tech", "soft"]):
        cls = "tbl-dept-eng"
    elif "prod" in dept:
        cls = "tbl-dept-prod"
    elif any(k in dept for k in ["design", "ui", "ux"]):
        cls = "tbl-dept-design"
    elif "sale" in dept:
        cls = "tbl-dept-sales"
    elif "market" in dept:
        cls = "tbl-dept-mktg"
    elif any(k in dept for k in ["hr", "people", "talent"]):
        cls = "tbl-dept-hr"
    elif any(k in dept for k in ["data", "analyt", "ai", "bi"]):
        cls = "tbl-dept-data"
    else:
        cls = "tbl-dept-ops"
    return f'<span class="tbl-dept-badge {cls}">{department or "General"}</span>'

def get_status_badge_html(status: str) -> str:
    s = (status or "").lower()
    if any(k in s for k in ["act", "comp", "pass"]):
        return f'<span class="tbl-badge tbl-badge-green"><span class="tbl-badge-dot"></span>{status}</span>'
    elif any(k in s for k in ["leave", "prog", "pend"]):
        return f'<span class="tbl-badge tbl-badge-yellow"><span class="tbl-badge-dot"></span>{status}</span>'
    elif any(k in s for k in ["term", "fail", "over"]):
        return f'<span class="tbl-badge tbl-badge-red"><span class="tbl-badge-dot"></span>{status}</span>'
    else:
        return f'<span class="tbl-badge tbl-badge-blue"><span class="tbl-badge-dot"></span>{status}</span>'

def get_rating_badge_html(score: Any) -> str:
    try:
        val = float(score)
    except (ValueError, TypeError):
        val = 0.0
    if val >= 4.5:
        tier_cls = "tbl-rating-top"
        label = f"{val:.1f} Top Performer"
    elif val >= 3.8:
        tier_cls = "tbl-rating-strong"
        label = f"{val:.1f} Strong"
    elif val >= 3.0:
        tier_cls = "tbl-rating-good"
        label = f"{val:.1f} Meets Target"
    elif val > 0.0:
        tier_cls = "tbl-rating-dev"
        label = f"{val:.1f} Development"
    else:
        tier_cls = "tbl-rating-dev"
        label = "Unrated"
    return f'<span class="tbl-rating-pill {tier_cls}">{label}</span>'

def get_priority_badge_html(priority: str) -> str:
    p = (priority or "").lower()
    if any(k in p for k in ["high", "crit", "urgent"]):
        return f'<span class="tbl-badge tbl-priority-high">{priority}</span>'
    elif "med" in p:
        return f'<span class="tbl-badge tbl-priority-med">{priority}</span>'
    else:
        return f'<span class="tbl-badge tbl-priority-low">{priority}</span>'

def get_prof_badge_html(level: str) -> str:
    l = (level or "").lower()
    if "exp" in l or "4" in l:
        return f'<span class="tbl-badge tbl-prof-expert">{level}</span>'
    elif "adv" in l or "3" in l:
        return f'<span class="tbl-badge tbl-prof-adv">{level}</span>'
    elif "inter" in l or "2" in l:
        return f'<span class="tbl-badge tbl-prof-int">{level}</span>'
    else:
        return f'<span class="tbl-badge tbl-prof-beg">{level}</span>'

def render_colored_employee_table(emp_results: List[Dict[str, Any]]) -> str:
    if not emp_results:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #EFF6FF; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("employees", size=26, color="#2563EB")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Workforce Records Found</div>
            <div style="font-size: 0.84rem; color: #64748B;">No employees match the current filters or registered in this organization.</div>
        </div>"""
    rows = []
    for emp in emp_results:
        score = emp.get("avg_rating") or 0.0
        pct = min(100, max(0, int((score / 5.0) * 100)))
        bar_color = "#8B5CF6" if score >= 4.5 else ("#10B981" if score >= 3.8 else ("#3B82F6" if score >= 3.0 else "#F59E0B"))
        initial = (emp.get("name") or "E")[:1].upper()
        skills_summary = emp.get("primary_skills") or "—"
        if len(skills_summary) > 28:
            skills_summary = skills_summary[:26] + ".."
        date_joined = emp.get("joining_date") or emp.get("created_at", "")[:10] or "—"
        org_label = emp.get("org_name") or emp.get("org_id") or "Talent Growth"
        acc_status = emp.get("account_status") or "Active"
        acc_status_badge = get_status_badge_html(acc_status)

        rows.append(
            f"""<tr>
                <td><span class="tbl-id-pill">{emp.get('employee_id', '')}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 9px;">
                        <div style="width: 28px; height: 28px; border-radius: 8px; background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 0.76rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {initial}
                        </div>
                        <div>
                            <div style="font-weight: 700; color: #0F172A;">{emp.get('name', '')}</div>
                            <div style="font-size: 0.76rem; color: #64748B;">{emp.get('email', '') or '—'}</div>
                        </div>
                    </div>
                </td>
                <td><span style="font-size: 0.80rem; font-weight: 600; color: #475569;">{org_label}</span></td>
                <td>{get_dept_badge_html(emp.get('department', ''))}</td>
                <td><span style="font-weight: 600; color: #334155;">{emp.get('designation', '')}</span></td>
                <td><span style="font-size: 0.82rem; color: #64748B;">{date_joined}</span></td>
                <td><span style="font-size: 0.82rem; color: #2563EB; font-weight: 500;" title="{emp.get('primary_skills', '')}">{skills_summary}</span></td>
                <td>
                    <div class="tbl-progress-container">
                        <div class="tbl-progress-track">
                            <div class="tbl-progress-bar" style="width: {pct}%; background: {bar_color};"></div>
                        </div>
                        {get_rating_badge_html(score)}
                    </div>
                </td>
                <td>{acc_status_badge}</td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Emp ID</th>
                    <th>Full Name & Email</th>
                    <th>Organization</th>
                    <th>Department</th>
                    <th>Job Title</th>
                    <th>Date Joined</th>
                    <th>Skills Summary</th>
                    <th>Performance</th>
                    <th>Account Status</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_review_table(reviews_list: List[Dict[str, Any]]) -> str:
    if not reviews_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #F3E8FF; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("star", size=26, color="#8B5CF6")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Performance Evaluations Recorded</div>
            <div style="font-size: 0.84rem; color: #64748B;">Conduct a performance review to establish historical evaluation trajectories.</div>
        </div>"""
    rows = []
    for r in reviews_list:
        score = float(r.get("performance_score") or 0.0)
        pct = min(100, max(0, int((score / 5.0) * 100)))
        bar_color = "#8B5CF6" if score >= 4.5 else ("#10B981" if score >= 3.8 else ("#3B82F6" if score >= 3.0 else "#F59E0B"))
        dt = (r.get("created_at") or "")[:10]
        initial = (r.get("employee_name") or "E")[:1].upper()
        rows.append(
            f"""<tr>
                <td><span class="tbl-id-pill">{r.get('employee_id', '')}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 9px;">
                        <div style="width: 28px; height: 28px; border-radius: 8px; background: #F3E8FF; color: #8B5CF6; font-weight: 700; font-size: 0.76rem; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            {initial}
                        </div>
                        <div>
                            <div style="font-weight: 700; color: #0F172A;">{r.get('employee_name', '')}</div>
                            <div style="font-size: 0.76rem; color: #64748B;">{r.get('designation', '')}</div>
                        </div>
                    </div>
                </td>
                <td>{get_dept_badge_html(r.get('department', ''))}</td>
                <td><span class="tbl-badge tbl-badge-blue">{r.get('review_period', '')}</span></td>
                <td>
                    <div class="tbl-progress-container">
                        <div class="tbl-progress-track">
                            <div class="tbl-progress-bar" style="width: {pct}%; background: {bar_color};"></div>
                        </div>
                        {get_rating_badge_html(score)}
                    </div>
                </td>
                <td>
                    <div style="font-size: 0.8rem; color: #065F46; font-weight: 600; display: flex; align-items: center; gap: 5px;">
                        {get_svg_icon("check", size=13, color="#10B981")}
                        <span>{r.get('strengths') or 'Consistency'}</span>
                    </div>
                    <div style="font-size: 0.76rem; color: #9A3412; display: flex; align-items: center; gap: 5px; margin-top: 3px;">
                        {get_svg_icon("trending_up", size=13, color="#EA580C")}
                        <span>{r.get('improvements') or 'Leadership'}</span>
                    </div>
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 5px; font-family: monospace; font-size: 0.8rem; color: #64748B;">
                        {get_svg_icon("calendar", size=12, color="#94A3B8")}
                        <span>{dt}</span>
                    </div>
                </td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Emp ID</th>
                    <th>Employee</th>
                    <th>Department</th>
                    <th>Period</th>
                    <th>Rating & Score</th>
                    <th>Key Highlights</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_skills_table(skills_list: List[Dict[str, Any]]) -> str:
    if not skills_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #ECFDF5; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("skills", size=26, color="#10B981")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Competencies Cataloged Yet</div>
            <div style="font-size: 0.84rem; color: #64748B;">Add verified skills and proficiencies to evaluate benchmark readiness.</div>
        </div>"""
    rows = []
    for s in skills_list:
        rows.append(
            f"""<tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 7px;">
                        {get_svg_icon("code", size=15, color="#2563EB")}
                        <span style="font-weight: 700; color: #0F172A;">{s.get('skill_name', '')}</span>
                    </div>
                </td>
                <td><span class="tbl-badge tbl-badge-blue">{s.get('category', 'Technical')}</span></td>
                <td>{get_prof_badge_html(s.get('proficiency_level', 'Intermediate'))}</td>
                <td><span style="font-weight: 700; color: #475569;">{s.get('years_exp', 1.0)} yrs</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 5px; font-family: monospace; font-size: 0.8rem; color: #64748B;">
                        {get_svg_icon("calendar", size=12, color="#94A3B8")}
                        <span>{(s.get('last_updated') or '')[:10]}</span>
                    </div>
                </td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Competency</th>
                    <th>Category</th>
                    <th>Proficiency</th>
                    <th>Experience</th>
                    <th>Cataloged Date</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_gaps_table(gaps_list: List[Dict[str, Any]], levels_str: Dict[int, str]) -> str:
    if not gaps_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #ECFDF5; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("check", size=26, color="#10B981")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #065F46; margin-bottom: 4px;">All Competency Benchmarks Met</div>
            <div style="font-size: 0.84rem; color: #047857;">Employee exceeds or meets all role requirements for this benchmark target.</div>
        </div>"""
    rows = []
    for g in gaps_list:
        gap_val = g.get("gap", 0)
        if gap_val == 0:
            gap_badge = '<span class="tbl-badge tbl-gap-parity">Parity (0)</span>'
        elif gap_val == 1:
            gap_badge = '<span class="tbl-badge tbl-gap-warning">-1 Level</span>'
        else:
            gap_badge = f'<span class="tbl-badge tbl-gap-critical">-{gap_val} Levels</span>'
        curr_lvl = levels_str.get(g.get("current_level", 0), str(g.get("current_level", 0)))
        req_lvl = levels_str.get(g.get("required_level", 0), str(g.get("required_level", 0)))
        rows.append(
            f"""<tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 7px;">
                        {get_svg_icon("target", size=15, color="#2563EB")}
                        <span style="font-weight: 700; color: #0F172A;">{g.get('skill', '')}</span>
                    </div>
                </td>
                <td>{get_prof_badge_html(curr_lvl)}</td>
                <td>{get_prof_badge_html(req_lvl)}</td>
                <td>{gap_badge}</td>
                <td>{get_priority_badge_html(g.get('priority', 'Medium'))}</td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Competency</th>
                    <th>Current Level</th>
                    <th>Required Benchmark</th>
                    <th>Skill Shortfall</th>
                    <th>Priority</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_goals_table(goals_list: List[Dict[str, Any]]) -> str:
    if not goals_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #FFF7ED; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("goals", size=26, color="#EA580C")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Active Career Goals Recorded</div>
            <div style="font-size: 0.84rem; color: #64748B;">Set SMART milestone roadmaps to guide career progression.</div>
        </div>"""
    rows = []
    for g in goals_list:
        prog = int(g.get("progress") or 0)
        bar_color = "#10B981" if prog == 100 else ("#3B82F6" if prog >= 50 else "#F59E0B")
        rows.append(
            f"""<tr>
                <td>
                    <div style="display: flex; align-items: flex-start; gap: 8px;">
                        <span style="margin-top: 2px;">{get_svg_icon("target", size=15, color="#EA580C")}</span>
                        <div>
                            <div style="font-weight: 700; color: #0F172A;">{g.get('title', '')}</div>
                            <div style="font-size: 0.78rem; color: #64748B;">{str(g.get('description', ''))[:70]}...</div>
                        </div>
                    </div>
                </td>
                <td><span class="tbl-badge tbl-badge-purple">{g.get('target_designation', 'Target Role')}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 5px; font-family: monospace; font-size: 0.8rem; color: #475569;">
                        {get_svg_icon("calendar", size=12, color="#94A3B8")}
                        <span>{g.get('target_date', '')}</span>
                    </div>
                </td>
                <td>
                    <div class="tbl-progress-container">
                        <div class="tbl-progress-track">
                            <div class="tbl-progress-bar" style="width: {prog}%; background: {bar_color};"></div>
                        </div>
                        <span class="tbl-progress-text">{prog}%</span>
                    </div>
                </td>
                <td>{get_status_badge_html(g.get('status', 'In Progress'))}</td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Goal & Action Steps</th>
                    <th>Target Role</th>
                    <th>Target Date</th>
                    <th>Milestone Progress</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_training_table(trainings_list: List[Dict[str, Any]]) -> str:
    if not trainings_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #EFF6FF; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("award", size=26, color="#2563EB")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Training Courses Assigned</div>
            <div style="font-size: 0.84rem; color: #64748B;">Assign target upskilling programs to address competency shortfalls.</div>
        </div>"""
    rows = []
    for t in trainings_list:
        score = float(t.get("score") or 0.0)
        pct = min(100, max(0, int(score)))
        bar_color = "#10B981" if pct >= 80 else ("#3B82F6" if pct >= 60 else "#F59E0B")
        rows.append(
            f"""<tr>
                <td><span class="tbl-id-pill">{t.get('employee_id', '')}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 7px;">
                        {get_svg_icon("award", size=15, color="#2563EB")}
                        <span style="font-weight: 700; color: #0F172A;">{t.get('course_name', '')}</span>
                    </div>
                </td>
                <td><span class="tbl-badge tbl-badge-purple">{t.get('target_skill', '')}</span></td>
                <td><span style="color: #475569; font-size: 0.82rem;">{t.get('provider', '')}</span></td>
                <td>
                    <div style="display: flex; align-items: center; gap: 5px; font-family: monospace; font-size: 0.8rem; color: #64748B;">
                        {get_svg_icon("calendar", size=12, color="#94A3B8")}
                        <span>{t.get('target_completion_date', '')}</span>
                    </div>
                </td>
                <td>{get_status_badge_html(t.get('status', 'Enrolled'))}</td>
                <td>
                    <div class="tbl-progress-container">
                        <div class="tbl-progress-track">
                            <div class="tbl-progress-bar" style="width: {pct}%; background: {bar_color};"></div>
                        </div>
                        <span class="tbl-progress-text">{pct}%</span>
                    </div>
                </td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Emp ID</th>
                    <th>Course Title</th>
                    <th>Target Skill</th>
                    <th>Provider</th>
                    <th>Target Date</th>
                    <th>Status</th>
                    <th>Grade / Completion</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""

def render_colored_dept_summary_table(dept_summary_list: List[Dict[str, Any]]) -> str:
    if not dept_summary_list:
        return f"""<div class="corporate-table-wrapper" style="padding: 3rem 1.5rem; text-align: center;">
            <div style="width: 54px; height: 54px; border-radius: 50%; background: #EFF6FF; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                {get_svg_icon("building", size=26, color="#2563EB")}
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">No Department Metrics Available</div>
            <div style="font-size: 0.84rem; color: #64748B;">Department analytics will populate as employee reviews are completed.</div>
        </div>"""
    rows = []
    for ds in dept_summary_list:
        avg_s = float(ds.get("avg_score") or 0.0)
        pct = min(100, max(0, int((avg_s / 5.0) * 100)))
        bar_color = "#8B5CF6" if avg_s >= 4.5 else ("#10B981" if avg_s >= 3.8 else ("#3B82F6" if avg_s >= 3.0 else "#F59E0B"))
        rows.append(
            f"""<tr>
                <td>{get_dept_badge_html(ds.get('department', ''))}</td>
                <td><span class="tbl-badge tbl-badge-blue">{ds.get('employee_count', 0)} active</span></td>
                <td>
                    <div class="tbl-progress-container">
                        <div class="tbl-progress-track">
                            <div class="tbl-progress-bar" style="width: {pct}%; background: {bar_color};"></div>
                        </div>
                        {get_rating_badge_html(avg_s)}
                    </div>
                </td>
                <td><span style="font-weight: 700; color: #475569;">{ds.get('total_reviews', 0)} reviews</span></td>
            </tr>"""
        )
    return f"""<div class="corporate-table-wrapper">
        <table class="corporate-table">
            <thead>
                <tr>
                    <th>Department</th>
                    <th>Active Headcount</th>
                    <th>Average Performance Rating</th>
                    <th>Completed Reviews</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>"""



# ------------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ------------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_view" not in st.session_state:
    st.session_state.auth_view = "landing"
if "clear_emp_form_flag" not in st.session_state:
    st.session_state.clear_emp_form_flag = False
if "quick_fill_role" not in st.session_state:
    st.session_state.quick_fill_role = None

# ------------------------------------------------------------------------------
# 1. DEDICATED CORPORATE LANDING WEBPAGE
# ------------------------------------------------------------------------------
def landing_webpage():
    # Top Glassmorphic Navbar
    render_html(
        f"""
        <div style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(12px); border: 1px solid #E2E8F0; border-radius: 16px; padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04);">
            <div style="display: flex; align-items: center; gap: 12px;">
                {get_svg_icon("brand_logo", size=36)}
                <div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">Talent Growth</div>
                    <div style="font-size: 0.78rem; color: #64748B; font-weight: 500;">Talent Management Platform for Employee Performance and Career Growth</div>
                </div>
            </div>
        </div>
        """
    )

    col_nav_sp, col_nav_login, col_nav_reg = st.columns([6, 1.8, 2.2], gap="small")
    with col_nav_login:
        if st.button("Sign In", key="nav_btn_login", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "login"
            st.rerun()
    with col_nav_reg:
        if st.button("Create Account", key="nav_btn_reg", use_container_width=True, type="primary"):
            st.session_state.auth_view = "register"
            st.rerun()

    # HERO SECTION (High-Impact Enterprise Banner with Radial Dark Aesthetic)
    render_html(
        f"""
        <div class="webpage-hero-modern">
            <div style="max-width: 860px; position: relative; z-index: 2;">
                <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(99, 102, 241, 0.18); border: 1px solid rgba(129, 140, 248, 0.35); padding: 5px 14px; border-radius: 9999px; color: #C7D2FE; font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 1.25rem;">
                    {get_svg_icon("sparkles", size=14, color="#A5B4FC")}
                    Talent Management Platform for Employee Performance and Career Growth
                </div>
                <h1 style="font-size: 2.9rem; font-weight: 900; color: #FFFFFF; line-height: 1.15; letter-spacing: -0.03em; margin: 0 0 1rem 0;">
                    Build Better Teams,<br/>
                    <span class="hero-gradient-text">Grow Together</span>
                </h1>
                <p style="color: #94A3B8; font-size: 1.08rem; line-height: 1.6; margin-bottom: 1.85rem; max-width: 740px;">
                    Talent management for a brighter future. Elevate workforce performance, discover skill benchmarks, and navigate personalized career pathways with intelligent evaluations and goal roadmaps.
                </p>
                <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 2rem;">
                    <div class="hero-feature-pill">
                        {get_svg_icon("employees", size=16, color="#60A5FA")} Workforce Directory & Profiles
                    </div>
                    <div class="hero-feature-pill">
                        {get_svg_icon("performance", size=16, color="#34D399")} Performance Trajectory Reviews
                    </div>
                    <div class="hero-feature-pill">
                        {get_svg_icon("skills", size=16, color="#C084FC")} 10-Role Skill Benchmarks
                    </div>
                    <div class="hero-feature-pill">
                        {get_svg_icon("goals", size=16, color="#FB923C")} SMART Milestone Roadmap
                    </div>
                </div>
            </div>
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 1.1rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.82rem; color: #94A3B8; position: relative; z-index: 2;">
                <span style="display: flex; align-items: center; gap: 6px;">
                    {get_svg_icon("shield", size=15, color="#818CF8")}
                    Encrypted Authentication & Local SQLite Database
                </span>
                <span style="display: flex; align-items: center; gap: 6px;">
                    {get_svg_icon("check", size=15, color="#34D399")}
                    Enterprise Production Ready
                </span>
            </div>
        </div>
        """
    )

    # SEPARATED SECTION 1: 1-CLICK QUICK DEMO SIGN-IN
    render_html(
        f"""
        <div style="margin: 2.2rem 0 1.25rem 0;">
            <div style="display: inline-flex; align-items: center; gap: 6px; background: #EFF6FF; border: 1px solid #DBEAFE; color: #2563EB; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                {get_svg_icon("sparkles", size=13, color="#2563EB")} Instant Live Demo
            </div>
            <h2 style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 0 0 6px 0; letter-spacing: -0.02em;">
                1-Click Quick Demo Sign-In
            </h2>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0 0 1.25rem 0;">
                Select a pre-configured enterprise role below to test full platform capabilities immediately without entering passwords.
            </p>
        </div>
        """
    )

    col_d1, col_d2, col_d3 = st.columns(3, gap="medium")

    with col_d1:
        render_html(
            f"""
            <div class="demo-role-card demo-role-admin">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #FEF3C7; color: #92400E; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(245, 158, 11, 0.15);">
                        {get_svg_icon("shield", size=22, color="#92400E")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 800; color: #92400E; background: #FEF3C7; border: 1px solid #FDE68A; padding: 3px 8px; border-radius: 9999px;">ADMIN</span>
                </div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">HR Administrator</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">admin@talentgrowth.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Full administrative governance, workforce directory CRUD, performance trajectory tracking, bulk CSV imports, and ATS studio.
                </p>
                <div style="font-size: 0.78rem; color: #047857; margin-bottom: 1.1rem; display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>Workforce CRUD & Lifecycle</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>Trajectory Reviews & Analytics</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>Bulk CSV & Excel Importer</span></div>
                </div>
            </div>
            """
        )
        if st.button("Sign In as HR Admin", key="landing_btn_admin", use_container_width=True, type="primary"):
            admin_acc = login("admin@talentgrowth.com", "Admin@12345") or login("admin@talentsphere.com", "Admin@12345")
            if admin_acc:
                st.session_state.user = admin_acc
                st.session_state.current_page = "Dashboard"
                st.session_state.auth_view = "landing"
                st.rerun()
            else:
                st.error("Authentication failed. Please verify HR Admin credentials.")

    with col_d2:
        render_html(
            f"""
            <div class="demo-role-card demo-role-eng">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #EFF6FF; color: #2563EB; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.15);">
                        {get_svg_icon("code", size=22, color="#2563EB")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 800; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 3px 8px; border-radius: 9999px;">ENGINEER</span>
                </div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">Alex Morgan</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">alex@company.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Employee self-service portal, 10-role skill benchmark matrix, target readiness radar, and SMART milestones roadmap.
                </p>
                <div style="font-size: 0.78rem; color: #1D4ED8; margin-bottom: 1.1rem; display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#2563EB")} <span>10-Role Benchmark Matrix</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#2563EB")} <span>Competency Gap Simulator</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#2563EB")} <span>SMART Career Goals Roadmap</span></div>
                </div>
            </div>
            """
        )
        if st.button("Sign In as Alex Morgan", key="landing_btn_alex", use_container_width=True, type="primary"):
            emp_acc = login("alex@company.com", "Password123")
            if emp_acc:
                st.session_state.user = emp_acc
                st.session_state.current_page = "Dashboard"
                st.session_state.auth_view = "landing"
                st.rerun()
            else:
                st.error("Authentication failed. Please verify employee credentials.")

    with col_d3:
        render_html(
            f"""
            <div class="demo-role-card demo-role-analyst">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 12px; background: #ECFDF5; color: #065F46; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(16, 185, 129, 0.15);">
                        {get_svg_icon("analytics", size=22, color="#065F46")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 800; color: #065F46; background: #ECFDF5; border: 1px solid #A7F3D0; padding: 3px 8px; border-radius: 9999px;">DATA ANALYST</span>
                </div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">Ravi Kumar</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">ravi@company.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Competency portfolio tracking, historical review feedback, department skill gap analytics, and promotion milestones.
                </p>
                <div style="font-size: 0.78rem; color: #047857; margin-bottom: 1.1rem; display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>Competency Portfolio Tracking</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>Training & Upskilling Records</span></div>
                    <div style="display: flex; align-items: center; gap: 7px;">{get_svg_icon("check", size=13, color="#10B981")} <span>AI Career Coach & Strategy</span></div>
                </div>
            </div>
            """
        )
        if st.button("Sign In as Ravi Kumar", key="landing_btn_ravi", use_container_width=True, type="primary"):
            ravi_acc = login("ravi@company.com", "Password123")
            if ravi_acc:
                st.session_state.user = ravi_acc
                st.session_state.current_page = "Dashboard"
                st.session_state.auth_view = "landing"
                st.rerun()
            else:
                st.error("Authentication failed. Please verify employee credentials.")

    # SEPARATED SECTION 2: ENTERPRISE PLATFORM CAPABILITIES
    render_html(
        f"""
        <div style="margin: 2.75rem 0 1.25rem 0;">
            <div style="display: inline-flex; align-items: center; gap: 6px; background: #F8FAFC; border: 1px solid #E2E8F0; color: #475569; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
                {get_svg_icon("layers", size=13, color="#475569")} Core Capabilities
            </div>
            <h2 style="font-size: 1.85rem; font-weight: 800; color: #0F172A; margin: 0 0 6px 0; letter-spacing: -0.02em;">
                Enterprise Architecture Modules
            </h2>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0 0 1.5rem 0;">
                Engineered for scaling human talent across modern corporate departments.
            </p>
        </div>
        """
    )

    col_m1, col_m2 = st.columns(2, gap="medium")
    with col_m1:
        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03); margin-bottom: 0.85rem;">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #EFF6FF; color: #2563EB; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {get_svg_icon("employees", size=22, color="#2563EB")}
                    </div>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">Workforce Directory & Lifecycle</div>
                        <p style="font-size: 0.88rem; color: #64748B; line-height: 1.5; margin: 0;">
                            Centralized employee records with multi-attribute filtering, live search, employment status management, and instant Excel/CSV dataset onboarding.
                        </p>
                    </div>
                </div>
            </div>
            """
        )
        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #F5F3FF; color: #8B5CF6; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {get_svg_icon("skills", size=22, color="#8B5CF6")}
                    </div>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">10-Role Benchmark Competency Matrices</div>
                        <p style="font-size: 0.88rem; color: #64748B; line-height: 1.5; margin: 0;">
                            Standardized competency benchmarks for 10 corporate roles. Calculates target vs. actual proficiencies with automated skill gap visualizations.
                        </p>
                    </div>
                </div>
            </div>
            """
        )

    with col_m2:
        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03); margin-bottom: 0.85rem;">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #ECFDF5; color: #065F46; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {get_svg_icon("performance", size=22, color="#10B981")}
                    </div>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">Performance Reviews & Trajectory</div>
                        <p style="font-size: 0.88rem; color: #64748B; line-height: 1.5; margin: 0;">
                            Objective 1.0–5.0 evaluation cycles, department rating averages, qualitative feedback logging, and interactive historical rating trend charts.
                        </p>
                    </div>
                </div>
            </div>
            """
        )
        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: flex-start; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #FFF7ED; color: #C2410C; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                        {get_svg_icon("goals", size=22, color="#EA580C")}
                    </div>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; margin-bottom: 4px;">SMART Career Milestone Roadmap</div>
                        <p style="font-size: 0.88rem; color: #64748B; line-height: 1.5; margin: 0;">
                            Structured milestone tracking, due date monitoring, completion metrics, and AI-assisted personalized development roadmaps.
                        </p>
                    </div>
                </div>
            </div>
            """
        )

    # SEPARATED SECTION 3: CREDENTIALS CALL-TO-ACTION (SEPARATE CONTAINER)
    render_html(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 16px; padding: 2rem 2.2rem; margin: 2.75rem 0 1.25rem 0; text-align: center;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: #EFF6FF; color: #2563EB; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.85rem;">
                {get_svg_icon("lock", size=24, color="#2563EB")}
            </div>
            <h3 style="font-size: 1.45rem; font-weight: 800; color: #0F172A; margin: 0 0 6px 0;">Have Corporate Credentials?</h3>
            <p style="color: #64748B; font-size: 0.92rem; max-width: 540px; margin: 0 auto 1.5rem auto;">
                Sign in with your organization email and secure password, or register a new administrator / employee account.
            </p>
        </div>
        """
    )

    c_cta1, c_cta_sp1, c_cta2 = st.columns([1.5, 0.2, 1.5], gap="small")
    with c_cta1:
        if st.button("Sign In with Email & Password", key="cta_btn_signin", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "login"
            st.rerun()
    with c_cta2:
        if st.button("Create a New Account", key="cta_btn_reg", use_container_width=True, type="primary"):
            st.session_state.auth_view = "register"
            st.rerun()

    # Footer
    render_html(
        """
        <div style="border-top: 1px solid #E2E8F0; margin-top: 3rem; padding-top: 1.5rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.82rem; color: #94A3B8;">
            <div>&copy; 2026 Talent Growth. All rights reserved. Talent Management Platform for Employee Performance and Career Growth.</div>
            <div style="display: flex; gap: 16px;">
                <span>Security & Privacy</span>
                <span>Terms of Service</span>
                <span>Local SQLite Storage</span>
            </div>
        </div>
        """
    )


# ------------------------------------------------------------------------------
# 2. DEDICATED SIGN IN PAGE (WITH TOP-LEFT BACK BUTTON)
# ------------------------------------------------------------------------------
def login_page():
    # Top Bar: Top-left "Back to Home" button & Logo on right
    col_back, col_spacer, col_logo = st.columns([2.5, 4.5, 3], gap="small")
    with col_back:
        if st.button("Back to Home", key="btn_login_back_home", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "landing"
            st.rerun()
    with col_logo:
        render_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 4px;">
                {get_svg_icon("brand_logo", size=28)}
                <span style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">Talent Growth</span>
            </div>
            """
        )

    st.markdown("<div style='border-bottom: 1px solid #E2E8F0; margin: 0.75rem 0 1.75rem 0;'></div>", unsafe_allow_html=True)

    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        with st.container(border=True):
            render_html(
                f"""
                <div style="text-align: center; margin-bottom: 1.25rem;">
                    <div style="width: 48px; height: 48px; border-radius: 12px; background: #EFF6FF; border: 1px solid #DBEAFE; display: inline-flex; align-items: center; justify-content: center; color: #2563EB; margin-bottom: 0.75rem;">
                        {get_svg_icon("lock", size=22, color="#2563EB")}
                    </div>
                    <h2 style="font-size: 1.65rem; font-weight: 800; color: #0F172A; margin: 0 0 4px 0;">Sign In to Your Account</h2>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">Enter your corporate email and password to access the platform.</p>
                </div>
                """
            )

            with st.form("dedicated_login_form"):
                email = st.text_input("Corporate Email Address", placeholder="name@company.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")

                c_rem, c_forgot = st.columns([1, 1])
                with c_rem:
                    remember_me = st.checkbox("Remember me", value=True)
                with c_forgot:
                    st.markdown("<div style='text-align: right; font-size: 0.85rem; color: #2563EB; font-weight: 600; padding-top: 4px;'>Forgot password?</div>", unsafe_allow_html=True)

                submit_login = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submit_login:
                if not email.strip() or not password.strip():
                    st.error("Please enter both email address and password.")
                else:
                    user_data = login(email.strip(), password.strip())
                    if user_data:
                        st.session_state.user = user_data
                        st.session_state.current_page = "Dashboard"
                        st.session_state.auth_view = "landing"
                        st.success(f"Welcome back, {user_data['name']}!")
                        st.rerun()
                    else:
                        st.error("Authentication failed: Invalid email or password. Please verify your credentials.")

            render_html("<div style='border-top: 1px solid #E2E8F0; margin: 1.25rem 0 0.85rem 0;'></div>")
            render_html("<div style='text-align: center; font-size: 0.86rem; color: #64748B; margin-bottom: 0.5rem;'>Don't have an account yet?</div>")
            if st.button("Create a New Account", key="btn_login_to_register", use_container_width=True, type="secondary"):
                st.session_state.auth_view = "register"
                st.rerun()

            render_html("<div style='text-align: center; font-size: 0.82rem; color: #94A3B8; margin: 0.75rem 0 0.35rem 0;'>Looking for instant demo access?</div>")
            if st.button("Try 1-Click Demo on Home Page", key="btn_login_to_demo", use_container_width=True, type="secondary"):
                st.session_state.auth_view = "landing"
                st.rerun()


# ------------------------------------------------------------------------------
# 3. DEDICATED CREATE ACCOUNT PAGE (WITH TOP-LEFT BACK BUTTON)
# ------------------------------------------------------------------------------
def register_page():
    # Top Bar: Top-left "Back to Home" button & Logo on right
    col_back, col_spacer, col_logo = st.columns([2.5, 4.5, 3], gap="small")
    with col_back:
        if st.button("Back to Home", key="btn_reg_back_home", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "landing"
            st.rerun()
    with col_logo:
        render_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 4px;">
                {get_svg_icon("brand_logo", size=28)}
                <span style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">Talent Growth</span>
            </div>
            """
        )

    st.markdown("<div style='border-bottom: 1px solid #E2E8F0; margin: 0.75rem 0 1.75rem 0;'></div>", unsafe_allow_html=True)

    col_l, col_center, col_r = st.columns([1, 1.4, 1])
    with col_center:
        with st.container(border=True):
            render_html(
                f"""
                <div style="text-align: center; margin-bottom: 1.25rem;">
                    <div style="width: 48px; height: 48px; border-radius: 12px; background: #ECFDF5; border: 1px solid #A7F3D0; display: inline-flex; align-items: center; justify-content: center; color: #10B981; margin-bottom: 0.75rem;">
                        {get_svg_icon("user_plus", size=22, color="#10B981")}
                    </div>
                    <h2 style="font-size: 1.65rem; font-weight: 800; color: #0F172A; margin: 0 0 4px 0;">Create Your Account</h2>
                    <p style="color: #64748B; font-size: 0.9rem; margin: 0;">Register to access talent assessments & growth tools.</p>
                </div>
                """
            )

            existing_orgs = list_organizations()
            org_options = [f"{o['name']} ({o['org_id']})" for o in existing_orgs] + ["Register New Organization"]

            name = st.text_input("Full Legal Name *", placeholder="e.g. Jordan Miller", key="reg_name")
            new_email = st.text_input("Corporate Email Address *", placeholder="jordan.miller@company.com", key="reg_email")
            new_password = st.text_input("Password (min 8 characters) *", type="password", placeholder="Set a secure password", key="reg_password")

            c_r1, c_r2 = st.columns(2)
            role = c_r1.selectbox(
                "Account Type *",
                ["employee", "admin"],
                format_func=lambda x: "Employee (Self-Service)" if x == "employee" else "HR Administrator",
                key="reg_role"
            )
            emp_code = c_r2.text_input("Employee ID (Optional - auto-assigned if empty)", placeholder="e.g. EMP208", key="reg_emp_code").strip().upper()

            # Organization Membership *
            st.markdown("<div style='font-size: 0.85rem; font-weight: 700; color: #1E293B; margin-top: 8px; margin-bottom: 4px;'>Organization Membership *</div>", unsafe_allow_html=True)
            sel_org_choice = st.selectbox(
                "Organization Membership *",
                org_options,
                index=0,
                key="reg_org_membership",
                label_visibility="collapsed"
            )

            is_new_org = (sel_org_choice == "Register New Organization")

            # Dynamically display Organization Name input field only when "Register New Organization" is selected
            new_org_name_val = ""
            if is_new_org:
                new_org_name_val = st.text_input(
                    "Organization Name *",
                    placeholder="Enter your organization name",
                    key="reg_new_org_name"
                )

            # HR Administrator verification/authorization key (Requirement 9)
            hr_auth_code_val = ""
            if role == "admin":
                hr_auth_code_val = st.text_input(
                    "HR Administrator Authorization Key *",
                    type="password",
                    placeholder="Enter HR verification key (default: HR2026)",
                    key="reg_hr_auth_key",
                    help="Authorized verification passkey required to access or create organization HR administrative controls."
                )

            c_dep1, c_dep2 = st.columns(2)
            depts_list = [
                "Engineering", "Product Management", "Data & Analytics",
                "Human Resources", "Finance & Operations", "Marketing & Growth",
                "Design", "Sales & Customer Success"
            ]
            dept_val = c_dep1.selectbox("Department *", depts_list, key="reg_dept")
            title_val = c_dep2.text_input("Job Title / Designation *", placeholder="e.g. Software Engineer / HRBP", key="reg_title")

            c_sk1, c_sk2 = st.columns([2, 1])
            skills_val = c_sk1.text_input("Primary Skills (Comma-separated)", value="Python, SQL, Communication", placeholder="e.g. Python, SQL, React, Data Analysis", key="reg_skills")
            exp_val = c_sk2.number_input("Years Experience", min_value=0.0, max_value=50.0, value=1.0, step=0.5, key="reg_exp")

            terms = st.checkbox("I agree to the Enterprise Talent Governance Terms", value=True, key="reg_terms")
            submit_reg = st.button("Create Account & Join Organization", type="primary", use_container_width=True, key="btn_submit_reg")

            if submit_reg:
                clean_name = (name or "").strip()
                clean_email = (new_email or "").strip()
                clean_pwd = new_password or ""
                clean_org_name = (new_org_name_val or "").strip() if is_new_org else ""

                if not clean_name:
                    st.error("Full Legal Name is required.")
                elif not clean_email or "@" not in clean_email or "." not in clean_email:
                    st.error("A valid corporate email address is required.")
                elif len(clean_pwd) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif is_new_org and not clean_org_name:
                    st.error("Organization Name is required when registering a new organization.")
                elif is_new_org and get_organization_by_name(clean_org_name):
                    existing = get_organization_by_name(clean_org_name)
                    st.error(f"An organization named '{existing['name']}' already exists ({existing['org_id']}). Please select it from the existing organizations dropdown or choose a different name.")
                elif not terms:
                    st.error("Please agree to the enterprise governance terms to proceed.")
                else:
                    if is_new_org:
                        chosen_org_id = None
                        chosen_org_name = clean_org_name
                    else:
                        for o in existing_orgs:
                            if f"{o['name']} ({o['org_id']})" == sel_org_choice:
                                chosen_org_id = o["org_id"]
                                chosen_org_name = o["name"]
                                break
                        else:
                            chosen_org_id = "ORG-TALENT-01"
                            chosen_org_name = "Talent Growth Technologies"

                    ok, msg = register(
                        name=clean_name,
                        email=clean_email,
                        password=clean_pwd,
                        role=role,
                        employee_id=emp_code if emp_code else None,
                        org_id=chosen_org_id,
                        org_name=chosen_org_name,
                        department=dept_val,
                        job_title=title_val.strip() or ("Software Engineer" if role == "employee" else "HR Administrator"),
                        primary_skills=skills_val.strip() or "Python, SQL, Communication",
                        years_experience=exp_val,
                        is_new_org=is_new_org,
                        hr_verification_code=hr_auth_code_val if role == "admin" else None,
                        require_hr_approval=True
                    )
                    if ok:
                        st.success(f"{msg} A welcome email has been sent to {clean_email}.")
                        st.session_state.auth_view = "login"
                        st.rerun()
                    else:
                        st.error(msg)

            render_html("<div style='border-top: 1px solid #E2E8F0; margin: 1.25rem 0 0.85rem 0;'></div>")
            render_html("<div style='text-align: center; font-size: 0.86rem; color: #64748B; margin-bottom: 0.5rem;'>Already have an account?</div>")
            if st.button("Sign In to Existing Account", key="btn_reg_to_login", use_container_width=True, type="secondary"):
                st.session_state.auth_view = "login"
                st.rerun()


# ------------------------------------------------------------------------------
# ROUTING FOR UNAUTHENTICATED USERS
# ------------------------------------------------------------------------------
if not st.session_state.user:
    current_auth_view = st.session_state.get("auth_view", "landing")
    if current_auth_view == "login":
        login_page()
    elif current_auth_view == "register":
        register_page()
    else:
        landing_webpage()
    st.stop()

# ------------------------------------------------------------------------------
# AUTHENTICATED CONTEXT
# ------------------------------------------------------------------------------
user = st.session_state.get("user") or {}
uid = user.get("id", 1)
is_admin = (user.get("role") == "admin" and user.get("status") != "Pending Approval")
is_pending_hr = (user.get("role") == "admin" and user.get("status") == "Pending Approval")
emp_id = user.get("employee_id") or f"EMP{uid:03d}"
org_id = user.get("org_id") or "ORG-TALENT-01"
org_name = user.get("org_name") or "Talent Growth Technologies"
profile = get_profile(uid)
skills = list_skills(uid)

# Initials for avatar
name_parts = (user.get("name") or "User").strip().split()
initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper()

def navigate_to(target_page: str):
    alias_map = {
        "Skills": "Skills & Assessment",
        "Skills & Competency Matrix": "Skills & Assessment",
        "Skills & Assessments": "Skills & Assessment",
        "Career Goals": "Growth Progress" if not is_admin else "Career Goals",
        "Career Direction & Gaps": "Career Direction",
        "ATS Resume Studio": "Resume Studio",
        "Reports": "Career Report" if not is_admin else "Reports",
        "AI Career Coach": "Career Coach"
    }
    st.session_state.page_to_navigate = alias_map.get(target_page, target_page)
    st.rerun()

# ------------------------------------------------------------------------------
# SIDEBAR STATE MANAGEMENT & ROLE-BASED ACCESS CONTROL
# ------------------------------------------------------------------------------
if "sidebar_expanded" not in st.session_state:
    st.session_state.sidebar_expanded = True

def toggle_sidebar():
    st.session_state.sidebar_expanded = not st.session_state.get("sidebar_expanded", True)

is_expanded = st.session_state.get("sidebar_expanded", True)

# Enforce backend role permissions (Employees cannot access HR Administrator sections)
if not is_admin and st.session_state.get("current_page") in ["Employees", "Performance", "Reports", "Career Goals"]:
    st.session_state.current_page = "Dashboard"
    st.session_state.nav_radio = "Dashboard"

# Role-specific navigation pages list
if is_admin:
    active_pages = [
        "Dashboard",
        "Employees",
        "Performance",
        "Skills & Assessment",
        "Career Goals",
        "Reports",
        "Resume Studio",
        "Settings"
    ]
else:
    active_pages = [
        "Dashboard",
        "My Profile",
        "Resume Studio",
        "Skills & Assessment",
        "Career Direction",
        "Role Match & Gaps",
        "Career Coach",
        "Growth Progress",
        "Career Report",
        "Settings"
    ]

if "page_to_navigate" in st.session_state:
    target_nav = st.session_state.pop("page_to_navigate")
    if target_nav in active_pages:
        st.session_state.current_page = target_nav
        st.session_state.nav_radio = target_nav

if "current_page" not in st.session_state or st.session_state.current_page not in active_pages:
    st.session_state.current_page = "Dashboard"

if "nav_radio" not in st.session_state or st.session_state.nav_radio not in active_pages:
    st.session_state.nav_radio = st.session_state.current_page

def on_nav_change():
    st.session_state.current_page = st.session_state.nav_radio

# ------------------------------------------------------------------------------
# DYNAMIC SIDEBAR CSS (THEMES, EXPANSION, HORIZONTAL RADIO ALIGNMENT)
# ------------------------------------------------------------------------------
width_px = 285 if is_expanded else 68
pad_x = 0.9 if is_expanded else 0.35
label_pad = "0 12px" if is_expanded else "0"
label_justify = "flex-start" if is_expanded else "center"
circle_margin_right = "10px" if is_expanded else "0px"
text_display = "inline-flex" if is_expanded else "none"

if is_admin:
    # HR Administrator: Dark Navy Theme
    bg_color = "#0A1128"
    border_color = "#1E293B"
    text_color = "#FFFFFF"
    item_inactive_color = "#94A3B8"
    circle_inactive_border = "#64748B"
    item_hover_bg = "#16223F"
    item_hover_color = "#FFFFFF"
    circle_hover_border = "#94A3B8"
    active_bg = "#2563EB"
    active_text = "#FFFFFF"
    active_circle_border = "#FFFFFF"
    active_circle_bg = "#FFFFFF"
    active_circle_shadow = "inset 0 0 0 2.5px #2563EB"
    ham_bg = "#16223F"
    ham_border = "#334155"
    ham_color = "#FFFFFF"
    ham_hover_bg = "#1E293B"
    ham_hover_color = "#60A5FA"
    ham_hover_border = "#60A5FA"
    home_btn_bg = "transparent"
    home_btn_border = "#334155"
    home_btn_color = "#94A3B8"
    home_btn_hover_bg = "#16223F"
    home_btn_hover_color = "#FFFFFF"
    home_btn_hover_border = "#475569"
    signout_border = "#334155"
    signout_color = "#94A3B8"
    signout_hover_bg = "#16223F"
    signout_hover_color = "#F87171"
    signout_hover_border = "#EF4444"
else:
    # Employee: Light Ice-Blue Theme
    bg_color = "#EFF4F8"
    border_color = "#D9E4EC"
    text_color = "#102A43"
    item_inactive_color = "#627D98"
    circle_inactive_border = "#94A3B8"
    item_hover_bg = "#E2EBF2"
    item_hover_color = "#102A43"
    circle_hover_border = "#64748B"
    active_bg = "#E0F2FE"
    active_text = "#0284C7"
    active_circle_border = "#0284C7"
    active_circle_bg = "#0284C7"
    active_circle_shadow = "inset 0 0 0 2.5px #E0F2FE"
    ham_bg = "#FFFFFF"
    ham_border = "#CBD5E1"
    ham_color = "#0E2A38"
    ham_hover_bg = "#F1F5F9"
    ham_hover_color = "#0284C7"
    ham_hover_border = "#0284C7"
    home_btn_bg = "transparent"
    home_btn_border = "#D2E0EB"
    home_btn_color = "#627D98"
    home_btn_hover_bg = "#E2EBF2"
    home_btn_hover_color = "#102A43"
    home_btn_hover_border = "#BAC7D5"
    signout_border = "#D2E0EB"
    signout_color = "#627D98"
    signout_hover_bg = "#FEE2E2"
    signout_hover_color = "#DC2626"
    signout_hover_border = "#EF4444"

sidebar_dynamic_css = f"""
<style>
/* Lock Sidebar to Left Viewport and Guarantee Visibility */
html body [data-testid="stAppViewContainer"] section[data-testid="stSidebar"],
html body section[data-testid="stSidebar"],
section[data-testid="stSidebar"] {{
    position: fixed !important;
    top: 0 !important;
    bottom: 0 !important;
    left: 0 !important;
    transform: none !important;
    margin-left: 0 !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 1000 !important;
    height: 100vh !important;
    max-height: 100vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    min-width: {width_px}px !important;
    width: {width_px}px !important;
    max-width: {width_px}px !important;
    background-color: {bg_color} !important;
    border-right: 1px solid {border_color} !important;
    color: {text_color} !important;
    padding-left: {pad_x}rem !important;
    padding-right: {pad_x}rem !important;
    transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                min-width 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                max-width 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}

/* Position Main Content Immediately to Right of Sidebar (No Overlap, No Horizontal Cutoff) */
[data-testid="stAppViewContainer"] > section:nth-child(2),
[data-testid="stMain"] {{
    margin-left: {width_px}px !important;
    width: calc(100% - {width_px}px) !important;
    max-width: calc(100% - {width_px}px) !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
    transition: margin-left 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                width 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                max-width 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}

/* Ensure Block Container Fits Viewport Perfectly Without Overflow */
.main .block-container,
[data-testid="stMain"] [data-testid="block-container"],
[data-testid="stMain"] [data-testid="stMainBlockContainer"] {{
    padding-top: 1.2rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
    width: 100% !important;
    box-sizing: border-box !important;
    overflow-x: hidden !important;
}}

/* Prevent Any Global Horizontal Scroll on Canvas */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
    overflow-x: hidden !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
}}

@media screen and (max-width: 768px) {{
    [data-testid="stAppViewContainer"] > section:nth-child(2),
    [data-testid="stMain"] {{
        margin-left: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
    }}
}}

/* Completely Hide Streamlit Native Collapse Controls */
div[data-testid="collapsedControl"],
div[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}}

/* Three-Line Hamburger Button Styling (Sidebar) */
div.sidebar-ham-btn button {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    background: {ham_bg} !important;
    border: 1px solid {ham_border} !important;
    color: {ham_color} !important;
    border-radius: 8px !important;
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    cursor: pointer !important;
    padding: 0 !important;
    box-shadow: none !important;
    transition: all 0.18s ease !important;
}}
div.sidebar-ham-btn button:hover {{
    background: {ham_hover_bg} !important;
    color: {ham_hover_color} !important;
    border-color: {ham_hover_border} !important;
}}

/* Radio Group Container */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] {{
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
    width: 100% !important;
}}

/* Radio Button Label: Strictly single row, horizontal flexbox, vertically centered */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: {label_justify} !important;
    width: 100% !important;
    min-height: 40px !important;
    height: 40px !important;
    padding: {label_pad} !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease, color 0.15s ease !important;
}}

/* Radio Circle Outer Container (First Child) */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 18px !important;
    min-width: 18px !important;
    max-width: 18px !important;
    height: 18px !important;
    margin: 0 {circle_margin_right} 0 0 !important;
    padding: 0 !important;
    flex-shrink: 0 !important;
    flex-grow: 0 !important;
}}

/* The actual circle inside first-child */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child div {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 14px !important;
    height: 14px !important;
    min-width: 14px !important;
    min-height: 14px !important;
    border-radius: 50% !important;
    box-sizing: border-box !important;
    transition: all 0.15s ease-in-out !important;
}}

/* Inactive Radio Circle: Outlined Circle */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:not([data-checked="true"]):not(:has(input:checked)) > div:first-child div {{
    border: 2px solid {circle_inactive_border} !important;
    background: transparent !important;
}}

/* Inactive Row Hover */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:not([data-checked="true"]):not(:has(input:checked)):hover {{
    background-color: {item_hover_bg} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:not([data-checked="true"]):not(:has(input:checked)):hover p {{
    color: {item_hover_color} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:not([data-checked="true"]):not(:has(input:checked)):hover > div:first-child div {{
    border-color: {circle_hover_border} !important;
}}

/* Inactive Text */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:not([data-checked="true"]):not(:has(input:checked)) p {{
    color: {item_inactive_color} !important;
    font-weight: 500 !important;
}}

/* Active Row Highlight: Blue Background Pill */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background-color: {active_bg} !important;
    border-radius: 8px !important;
}}

/* Active Radio Circle: Filled Circle */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] > div:first-child div,
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) > div:first-child div {{
    border: 2px solid {active_circle_border} !important;
    background-color: {active_circle_bg} !important;
    box-shadow: {active_circle_shadow} !important;
}}

/* Active Text */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label[data-checked="true"] p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {{
    color: {active_text} !important;
    font-weight: 700 !important;
}}

/* Text Container (Second Child / Last Child) */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label > div:last-child {{
    display: {text_display} !important;
    align-items: center !important;
    flex: 1 1 auto !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
}}

/* Markdown Container & Paragraph */
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] label p {{
    display: inline-block !important;
    margin: 0 !important;
    padding: 0 !important;
    font-size: 0.93rem !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}}


/* Sidebar Sign Out Button */
section[data-testid="stSidebar"] button[key="btn_sidebar_sign_out"],
section[data-testid="stSidebar"] button[key="btn_sidebar_signout_collapsed"] {{
    background: transparent !important;
    border: 1px solid {signout_border} !important;
    color: {signout_color} !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-size: 0.90rem !important;
    width: 100% !important;
    transition: all 0.18s ease !important;
}}
section[data-testid="stSidebar"] button[key="btn_sidebar_sign_out"]:hover,
section[data-testid="stSidebar"] button[key="btn_sidebar_signout_collapsed"]:hover {{
    background: {signout_hover_bg} !important;
    color: {signout_hover_color} !important;
    border-color: {signout_hover_border} !important;
}}
</style>
"""
st.markdown(sidebar_dynamic_css, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# REUSABLE SIDEBAR COMPONENT (HR ADMINISTRATOR & EMPLOYEE)
# ------------------------------------------------------------------------------
def render_app_sidebar(is_admin: bool, user: dict, active_pages: list) -> str:
    """Renders the shared sidebar component with Talent Growth branding, radio items, and Back to Home button."""
    with st.sidebar:
        if is_expanded:
            # 1. Branding: Hamburger Button (☰) + [Talent Growth Logo] Talent Growth
            col_ham, col_brand = st.columns([1.3, 4.7], gap="small")
            with col_ham:
                st.markdown('<div class="sidebar-ham-btn">', unsafe_allow_html=True)
                st.button("☰", key="sidebar_hamburger_btn", on_click=toggle_sidebar, help="Collapse sidebar (☰)")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_brand:
                brand_title_color = "#FFFFFF" if is_admin else "#0E2A38"
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; padding-top: 4px;">
                        {get_svg_icon("brand_logo", size=26)}
                        <span style="font-weight: 800; font-size: 1.20rem; color: {brand_title_color}; letter-spacing: -0.01em; line-height: 1;">Talent Growth</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # 2. Signed-in User Info & Role Subtitle
            user_subtitle_color = "#94A3B8" if is_admin else "#5A7383"
            role_title = "HR Administrator" if is_admin else "Employee"
            st.markdown(
                f"""
                <div style="font-size: 0.83rem; color: {user_subtitle_color}; margin-top: 2px; margin-bottom: 4px; padding-left: 2px;">
                    Signed in as <strong>{user.get('name', 'User')}</strong> &bull; {role_title}
                </div>
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(37, 99, 235, 0.12); border: 1px solid rgba(37, 99, 235, 0.28); border-radius: 6px; padding: 3px 8px; margin-bottom: 1.15rem; font-size: 0.76rem; color: {user_subtitle_color};">
                    <span style="font-weight: 700; color: #60A5FA;">{user.get('org_name', 'Talent Growth')}</span>
                    <span style="opacity: 0.75; font-family: monospace;">({user.get('org_id', 'ORG-TALENT-01')})</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 3. Radio Navigation Rows
            selected_nav = st.radio(
                "Navigation",
                active_pages,
                key="nav_radio",
                on_change=on_nav_change,
                label_visibility="collapsed"
            )
            st.session_state.current_page = selected_nav

            # 4. Spacing to bottom
            st.markdown("<div style='margin-top: 2.2rem;'></div>", unsafe_allow_html=True)

            # 5. Bottom Action: Single Sign out button
            if st.button("Sign out", use_container_width=True, type="secondary", key="btn_sidebar_sign_out"):
                st.session_state.user = None
                st.session_state.auth_view = "landing"
                st.session_state.current_page = "Dashboard"
                st.session_state.page_to_navigate = "Dashboard"
                st.rerun()

            return selected_nav

        else:
            # COLLAPSED NAVIGATION RAIL (~68px)
            st.markdown('<div class="sidebar-ham-btn" style="display: flex; justify-content: center; margin-bottom: 0.75rem;">', unsafe_allow_html=True)
            st.button("☰", key="sidebar_hamburger_btn_collapsed", on_click=toggle_sidebar, help="Expand sidebar (☰)")
            st.markdown('</div>', unsafe_allow_html=True)

            # Centered Compact Brand Logo
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; margin-bottom: 1.1rem;" title="Talent Growth">
                    {get_svg_icon("brand_logo", size=26)}
                </div>
                """,
                unsafe_allow_html=True
            )

            # Radio indicators (centered circles)
            selected_nav = st.radio(
                "Navigation",
                active_pages,
                key="nav_radio",
                on_change=on_nav_change,
                label_visibility="collapsed"
            )
            st.session_state.current_page = selected_nav

            # Bottom Action: Single compact Sign out button
            st.markdown("<div style='margin-top: 2.2rem;'></div>", unsafe_allow_html=True)
            if st.button("⎋", help="Sign out", use_container_width=True, type="secondary", key="btn_sidebar_signout_collapsed"):
                st.session_state.user = None
                st.session_state.auth_view = "landing"
                st.session_state.current_page = "Dashboard"
                st.session_state.page_to_navigate = "Dashboard"
                st.rerun()

            return selected_nav

page = render_app_sidebar(is_admin, user, active_pages)

def analysis_bundle():
    result = profile_analysis(profile, skills)
    result["match"] = role_match(profile.get("target_role", ""), skills, float(profile.get("years_experience") or 0))
    return result

# ------------------------------------------------------------------------------
# UNIVERSAL TOP BAR WITH BACK TO HOME & BREADCRUMBS
# ------------------------------------------------------------------------------
col_top_home, col_top_trail = st.columns([2.4, 7.6], gap="small")
with col_top_home:
    if st.button("Back to Home", key=f"btn_header_back_home_{page.replace(' ', '_').lower()}", type="secondary", use_container_width=True):
        navigate_to("Dashboard")

with col_top_trail:
    badge_color = "#2563EB" if is_admin else "#0284C7"
    badge_bg = "#EFF6FF" if is_admin else "#E0F2FE"
    badge_border = "#DBEAFE" if is_admin else "#BAE6FD"
    render_html(
        f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; font-size: 0.82rem; color: #64748B; padding-top: 6px;">
            <span style="display: inline-flex; align-items: center; gap: 6px; background: #F1F5F9; border: 1px solid #E2E8F0; padding: 3px 10px; border-radius: 9999px;">
                {get_svg_icon("user", size=13, color="#475569")}
                <strong>{user.get('name', 'User')}</strong> &bull; {user.get('role', 'employee').upper()}
            </span>
            <span style="color: #CBD5E1;">|</span>
            <span style="color: {badge_color}; font-weight: 700; background: {badge_bg}; border: 1px solid {badge_border}; padding: 3px 10px; border-radius: 9999px;">{page}</span>
        </div>
        """
    )
st.markdown("<div style='margin-bottom: 0.85rem;'></div>", unsafe_allow_html=True)

if is_pending_hr:
    st.warning("Your account is registered as an HR Administrator but is currently pending verification approval. Administrative control panels will be unlocked once approved.")
    with st.expander("Unlock HR Administrator Access with Authorization Key", expanded=True):
        c_v1, c_v2 = st.columns([3, 1])
        vcode = c_v1.text_input("Enter HR Authorization Key", type="password", key="inline_vkey", placeholder="e.g. HR2026")
        if c_v2.button("Verify & Activate", key="btn_inline_verify_hr", type="primary", use_container_width=True):
            ok_act, msg_act = verify_and_activate_hr_admin(uid, vcode)
            if ok_act:
                st.session_state.user["status"] = "Active"
                st.success("Verification successful! HR Administrator access granted.")
                st.rerun()
            else:
                st.error(msg_act)

# ==============================================================================
# 1. ADMIN: EXECUTIVE DASHBOARD
# ==============================================================================
if (page in ["Dashboard", "Executive Dashboard"] and is_admin):
    # Top Search & Profile Bar matching Image 1 & 2
    render_html(
        f"""
        <div class="top-header-bar">
            <div class="top-search-box">
                {get_svg_icon("search", size=18, color="#94A3B8")}
                <span>Search employees, skills, or departments...</span>
            </div>
            <div class="top-header-right">
                <div class="bell-pill" title="2 Unread Notifications">
                    {get_svg_icon("bell", size=18, color="#475569")}
                    <span class="dot">2</span>
                </div>
                <div class="header-user-badge">
                    <div class="header-user-avatar">{initials}</div>
                    <span class="header-user-name">{user.get('name', 'User')}</span>
                    <span style="font-size: 0.72rem; color: #2563EB; font-weight: 700; background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 9999px; padding: 2px 7px;">ADMIN</span>
                </div>
            </div>
        </div>
        """
    )

    # Professional Career Growth & Milestone Illustration (Replacing SVG shapes)
    career_growth_b64 = get_career_growth_illustration_b64()

    # Welcome Hero Banner with Career Growth Illustration
    org_display_name = user.get("org_name") or "Talent Growth Technologies"
    render_html(
        f"""
        <div style="background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 55%, #3B82F6 100%); border-radius: 16px; padding: 1.6rem 2.2rem; color: #FFFFFF; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 4px 18px rgba(37, 99, 235, 0.22); position: relative; overflow: hidden;">
            <div style="z-index: 2; max-width: 62%;">
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.16); border: 1px solid rgba(255, 255, 255, 0.28); padding: 4px 11px; border-radius: 9999px; font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">
                    {get_svg_icon("sparkles", size=13, color="#FEF08A")} Executive Talent Hub &bull; {org_display_name}
                </div>
                <div style="font-size: 1.85rem; font-weight: 800; color: #FFFFFF; line-height: 1.25; margin-bottom: 6px;">
                    Welcome back, {user.get('name', 'User')}
                </div>
                <div style="font-size: 0.96rem; color: rgba(255, 255, 255, 0.92); font-weight: 400; line-height: 1.5;">
                    Here's an overview of workforce performance, competency shortfalls, and career growth milestones.
                </div>
            </div>
            <div style="z-index: 2; flex-shrink: 0; display: flex; align-items: center; justify-content: flex-end;">
                <div style="background: #FFFFFF; border-radius: 14px; padding: 6px 14px; box-shadow: 0 6px 20px rgba(15, 23, 42, 0.14); display: flex; align-items: center; justify-content: center;">
                    <img src="data:image/png;base64,{career_growth_b64}" alt="Career Growth Trajectory" style="max-height: 110px; width: auto; object-fit: contain; display: block;" />
                </div>
            </div>
        </div>
        """
    )

    org_stats = get_org_dashboard_stats(org_id)
    employees = get_employees(org_id=org_id)
    reviews = get_performance_reviews(org_id=org_id)
    dept_summary = get_department_performance_summary(org_id=org_id)
    all_goals = get_goals(org_id=org_id)

    total_emp_count = org_stats["total_employees"]
    dept_count = org_stats["total_departments"]
    avg_perf = org_stats["avg_performance"]
    goal_completion_pct = org_stats["goal_completion_rate"]
    assessment_completion_pct = org_stats["assessment_completion_rate"]
    total_assessments = org_stats["total_assessments"]

    # Row of 4 Solid Vibrant KPI Cards matching Organization Scope
    render_html(
        f"""
        <div class="kpi-row-grid-vibrant">
            <div class="kpi-card-vibrant kpi-vibrant-blue">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("employees", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Organization Workforce</div>
                    <div class="kpi-vibrant-number">{total_emp_count}</div>
                    <div class="kpi-vibrant-sub">
                        {get_svg_icon("building", size=13, color="#FFFFFF")} {org_display_name} ({org_id})
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-green">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("building", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Departments</div>
                    <div class="kpi-vibrant-number">{dept_count}</div>
                    <div class="kpi-vibrant-sub">
                        {get_svg_icon("trending_up", size=13, color="#FFFFFF")} Active divisions
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-purple">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("star", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Avg Performance</div>
                    <div class="kpi-vibrant-number">{avg_perf} / 5.0</div>
                    <div class="kpi-vibrant-sub">
                        {get_svg_icon("trending_up", size=13, color="#FFFFFF")} Evaluated staff
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-orange">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("goals", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Skills & Goals Rate</div>
                    <div class="kpi-vibrant-number">{assessment_completion_pct}%</div>
                    <div class="kpi-vibrant-sub">
                        {get_svg_icon("check", size=13, color="#FFFFFF")} {goal_completion_pct}% goals achieved
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # Interactive Quick Actions Bar
    col_qa1, col_qa2, col_qa3, col_qa4 = st.columns(4)
    with col_qa1:
        if st.button("Add Employee", key="qa_bar_add_emp", use_container_width=True, type="primary"):
            navigate_to("Employees")
    with col_qa2:
        if st.button("Record Review", key="qa_bar_rec_rev", use_container_width=True):
            navigate_to("Performance")
    with col_qa3:
        if st.button("Add Skill", key="qa_bar_add_skill", use_container_width=True):
            navigate_to("Skills")
    with col_qa4:
        if st.button("Set Career Goal", key="qa_bar_set_goal", use_container_width=True):
            navigate_to("Career Goals")

    st.markdown("<div style='margin-bottom: 1.15rem;'></div>", unsafe_allow_html=True)

    # Middle Section: 2 Central Charts Filtered by Organization
    col_chart1, col_chart2 = st.columns([1.15, 1], gap="medium")
    with col_chart1:
        with st.container(border=True):
            c_trend_h1, c_trend_h2 = st.columns([1.8, 1])
            with c_trend_h1:
                render_html(
                    f"""
                    <div style="margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px;">
                        {get_svg_icon("analytics", size=18, color="#2563EB")}
                        <div style="font-weight: 800; font-size: 1.12rem; color: #0F172A;">Performance Rating Distribution</div>
                    </div>
                    """
                )
            with c_trend_h2:
                render_html(
                    f"""
                    <div style="text-align: right; padding-top: 2px;">
                        <span style="font-size: 0.82rem; font-weight: 600; color: #475569; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 10px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px;">
                            {get_svg_icon("building", size=13, color="#64748B")} {org_id}
                        </span>
                    </div>
                    """
                )

            perf_dist = org_stats["performance_distribution"]
            tiers = list(perf_dist.keys())
            counts = list(perf_dist.values())
            colors = ["#10B981", "#2563EB", "#F59E0B", "#EF4444"]

            fig_bar = go.Figure(go.Bar(
                x=tiers,
                y=counts,
                marker=dict(color=colors, line=dict(color="#CBD5E1", width=1)),
                text=counts,
                textposition='auto',
                hovertemplate="<b>%{x}</b><br>Reviews Count: <b>%{y}</b><extra></extra>"
            ))
            fig_bar.update_layout(
                margin=dict(l=15, r=15, t=15, b=15),
                height=280,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#F1F5F9", showgrid=False, tickfont=dict(color="#475569", size=11)),
                yaxis=dict(gridcolor="#F1F5F9", showgrid=True, dtick=1, tickfont=dict(color="#64748B", size=12))
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart2:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
                    <div style="font-weight: 800; font-size: 1.12rem; color: #0F172A;">Department Distribution</div>
                    <span style="font-size: 0.78rem; font-weight: 600; color: #64748B;">{org_id}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            dept_dist = org_stats["department_distribution"]
            if dept_dist:
                df_dept = pd.DataFrame(dept_dist)
                fig_donut = px.pie(
                    df_dept, values="count", names="department", hole=0.64,
                    color_discrete_sequence=['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4']
                )
                fig_donut.update_traces(
                    textinfo='none',
                    hoverinfo='label+percent',
                    hovertemplate="<b>%{label}</b><br>Personnel: <b>%{value}</b> (%{percent})<extra></extra>"
                )
                fig_donut.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=280,
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=11, color="#334155")),
                    annotations=[dict(
                        text=f"<b>{total_emp_count}</b><br><span style='font-size:12px;color:#64748B;'>Employees</span>",
                        x=0.5, y=0.5,
                        font_size=17,
                        showarrow=False
                    )]
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info(f"No department records registered yet for {org_name}.")

    # Bottom Section: 3 Organization-Isolated Cards
    col_w1, col_w2, col_w3 = st.columns(3, gap="medium")
    with col_w1:
        with st.container(border=True):
            c_pr1, c_pr2 = st.columns([1.5, 1])
            with c_pr1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("user_plus", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Recent Joiners</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_pr2:
                if st.button("View All", key="va_emp_dash", type="secondary", use_container_width=True):
                    navigate_to("Employees")

            recent_emps = org_stats["recent_joiners"]
            if recent_emps:
                rows_html = ""
                for re in recent_emps[:4]:
                    parts = re["name"].strip().split()
                    ini = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
                    rows_html += f"""
                    <div class="pending-review-row" style="padding: 7px 0; border-bottom: 1px solid #F1F5F9;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="pending-avatar" style="width: 32px; height: 32px; font-size: 0.78rem;">{ini}</div>
                            <div>
                                <div style="font-weight: 700; font-size: 0.86rem; color: #0F172A;">{re['name']}</div>
                                <div style="font-size: 0.75rem; color: #64748B;">{re['department']} &bull; {re['designation']}</div>
                            </div>
                        </div>
                        <span class="badge-status badge-active" style="font-size: 0.70rem; padding: 2px 7px;">{re['employee_id']}</span>
                    </div>
                    """
                render_html(f"<div style='margin-top: 4px;'>{rows_html}</div>")
            else:
                st.info(f"No recent joiners cataloged for {org_name}.")

    with col_w2:
        with st.container(border=True):
            c_sk1, c_sk2 = st.columns([1.5, 1])
            with c_sk1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("sparkles", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Org Skill Gaps</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_sk2:
                if st.button("View All", key="va_skills_dash", type="secondary", use_container_width=True):
                    navigate_to("Skills & Assessment")

            skills_dist = org_stats["skill_distribution"]
            if skills_dist:
                sk_rows_html = ""
                for s in skills_dist[:4]:
                    s_name = s.get("skill_name") or s.get("name") or "Skill"
                    s_cnt = s.get("count", 0)
                    s_avg = s.get("avg_level", 2)
                    pct = int(min(100, (s_avg / 4.0) * 100))
                    sk_rows_html += f"""
                    <div class="progress-widget-row" style="margin-bottom: 9px;">
                        <span class="progress-widget-name" style="font-size: 0.82rem; min-width: 95px;">{s_name} ({s_cnt})</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-blue" style="width: {pct}%;"></div>
                        </div>
                        <span class="progress-widget-pct" style="font-size: 0.80rem;">Lvl {s_avg}</span>
                    </div>
                    """
                render_html(f"<div style='margin-top: 12px;'>{sk_rows_html}</div>")
            else:
                st.info("No employee skills recorded in this organization yet.")

    with col_w3:
        with st.container(border=True):
            c_cg1, c_cg2 = st.columns([1.7, 1])
            with c_cg1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("goals", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Goals Milestone</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_cg2:
                if st.button("View All", key="va_goals_dash", type="secondary", use_container_width=True):
                    navigate_to("Career Goals")

            if all_goals:
                goal_rows_html = ""
                for g in all_goals[:4]:
                    p = g["progress"]
                    bar_class = "progress-bar-fill-green" if p >= 75 else ("progress-bar-fill-blue" if p >= 50 else "progress-bar-fill-purple")
                    goal_rows_html += f"""
                    <div class="progress-widget-row" style="margin-bottom: 9px;">
                        <span class="progress-widget-name" style="font-size: 0.82rem; min-width: 95px;" title="{g['title']}">{g['title'][:16]}..</span>
                        <div class="progress-bar-track">
                            <div class="{bar_class}" style="width: {p}%;"></div>
                        </div>
                        <span class="progress-widget-pct" style="font-size: 0.80rem;">{p}%</span>
                    </div>
                    """
                render_html(f"<div style='margin-top: 12px;'>{goal_rows_html}</div>")
            else:
                st.info(f"No active career goals recorded in {org_id}.")

# ==============================================================================
# 2. EMPLOYEE: MY CAREER DASHBOARD
# ==============================================================================
elif (page in ["Dashboard", "My Career Dashboard"] and not is_admin):
    completion, missing = profile_completion(profile, skills)
    analysis = analysis_bundle()
    goal_stats = get_goal_stats(uid)
    emp_record = get_employee_by_id(emp_id) if emp_id else None

    # Header matching Screenshot 4
    org_display_name = user.get("org_name") or "Talent Growth Technologies"
    render_html(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0F172A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0"/>
                    <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2"/>
                    <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8"/>
                    <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>
                </svg>
                <h1 style="font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin: 0;">
                    Good to see you, {user.get('name', 'User')}
                </h1>
            </div>
            <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 6px;">
                <span style="font-size: 0.95rem; color: #64748B;">Build a clearer view of where you are and what comes next.</span>
                <span style="display: inline-flex; align-items: center; gap: 5px; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 9999px; padding: 2px 10px; font-size: 0.78rem; font-weight: 700; color: #1D4ED8;">
                    {get_svg_icon("building", size=13, color="#2563EB")} {org_display_name} <span style="font-family: monospace; font-size: 0.72rem; opacity: 0.8;">({org_id})</span>
                </span>
            </div>
        </div>
        """
    )

    # 4 Top Metrics Row - Solid Vibrant KPI Cards matching reference design
    comp_sub = "+ All sections complete" if completion >= 100 else ("+ Action needed" if completion == 0 else f"+{len(missing)} fields to add")
    
    strength_score = analysis.get("score", 0)
    if strength_score >= 80:
        strength_sub = "+ Top tier readiness"
    elif strength_score >= 50:
        strength_sub = "+ Strong profile"
    elif strength_score > 0:
        strength_sub = "+ Developing readiness"
    else:
        strength_sub = "+ Early stage profile"
        
    target_role_str = profile.get("target_role") or ""
    if target_role_str:
        role_label = (target_role_str[:14] + "..") if len(target_role_str) > 16 else target_role_str
        role_sub = f"vs {role_label}"
    else:
        role_sub = "+ Choose target role"
        
    skills_cnt = len(skills)
    skills_sub = f"+{skills_cnt} verified skills" if skills_cnt > 0 else "+ Add competencies"

    render_html(
        f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 2rem;">
            <!-- Profile Completion -->
            <div style="background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 48px; height: 48px; border-radius: 10px; background: #DBEAFE; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("user", size=24, color="#2563EB")}
                </div>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #1E293B; margin-bottom: 2px;">Profile completion</div>
                    <div style="font-size: 1.95rem; font-weight: 800; color: #0F172A; line-height: 1.15;">{completion}%</div>
                </div>
            </div>
            <!-- Profile Strength -->
            <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 48px; height: 48px; border-radius: 10px; background: #D1FAE5; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("trending_up", size=24, color="#059669")}
                </div>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #1E293B; margin-bottom: 2px;">Profile strength</div>
                    <div style="font-size: 1.95rem; font-weight: 800; color: #0F172A; line-height: 1.15;">{strength_score}/100</div>
                </div>
            </div>
            <!-- Target Role Match -->
            <div style="background: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 48px; height: 48px; border-radius: 10px; background: #EDE9FE; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("target", size=24, color="#7C3AED")}
                </div>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #1E293B; margin-bottom: 2px;">Target role match</div>
                    <div style="font-size: 1.95rem; font-weight: 800; color: #0F172A; line-height: 1.15;">{analysis['match']}%</div>
                </div>
            </div>
            <!-- Skills Recorded -->
            <div style="background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 48px; height: 48px; border-radius: 10px; background: #FFEDD5; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("star", size=24, color="#EA580C")}
                </div>
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #1E293B; margin-bottom: 2px;">Skills recorded</div>
                    <div style="font-size: 1.95rem; font-weight: 800; color: #0F172A; line-height: 1.15;">{skills_cnt}</div>
                </div>
            </div>
        </div>
        """
    )

    col_dash_left, col_dash_right = st.columns([1.15, 1], gap="large")

    with col_dash_left:
        st.markdown("<h3 style='font-size: 1.35rem; font-weight: 800; color: #0F172A; margin-bottom: 1rem; display: flex; align-items: center; gap: 8px;'>Your next useful actions <span style='font-size: 1.1rem; color: #94A3B8;'>🔗</span></h3>", unsafe_allow_html=True)

        # Action Card 1: Profile Completeness
        if completion < 100:
            missing_text = ", ".join(missing[:4]) if missing else "Phone, summary, and experience"
            action_1_body = f"Add the missing sections: {missing_text}. This gives the career matching engine better evidence."
        else:
            action_1_body = "Your profile is fully populated. Review and update your certifications and latest deliverables as your career progresses."

        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; margin-bottom: 14px; display: flex; align-items: flex-start; gap: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 44px; height: 44px; border-radius: 10px; background: #EFF6FF; border: 1px solid #DBEAFE; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("reports", size=22, color="#2563EB")}
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 0.98rem; color: #0F172A; margin-bottom: 4px;">High &middot; Complete your professional profile</div>
                    <div style="font-size: 0.86rem; color: #64748B; line-height: 1.5;">{action_1_body}</div>
                </div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; margin-bottom: 14px; display: flex; align-items: flex-start; gap: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 44px; height: 44px; border-radius: 10px; background: #ECFDF5; border: 1px solid #A7F3D0; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    {get_svg_icon("reports", size=22, color="#059669")}
                </div>
                <div>
                    <div style="font-weight: 800; font-size: 0.98rem; color: #0F172A; margin-bottom: 4px;">Medium &middot; Create a role-aligned resume</div>
                    <div style="font-size: 0.86rem; color: #64748B; line-height: 1.5;">Use your profile details to draft an ATS-friendly resume and add measurable outcomes drawn from your actual work.</div>
                </div>
            </div>
            """
        )

        # Collapsible: Profile sections to complete
        with st.expander("Profile sections to complete"):
            if missing:
                st.markdown(f"**Still to add:** {', '.join(missing)}")
                if st.button("Complete Profile Now", key="dash_goto_prof_btn"):
                    navigate_to("My Profile")
            else:
                st.success("All primary profile sections are complete!")
                if st.button("Review Profile Details", key="dash_rev_prof_btn"):
                    navigate_to("My Profile")

    with col_dash_right:
        st.markdown("<h3 style='font-size: 1.35rem; font-weight: 800; color: #0F172A; margin-bottom: 1rem;'>Career snapshot</h3>", unsafe_allow_html=True)

        current_role_disp = profile.get('job_title') or (emp_record['designation'] if emp_record else "Add your current role")
        target_role_disp = profile.get('target_role') or "Choose a target role"

        render_html(
            f"""
            <div style="font-size: 0.95rem; color: #0F172A; line-height: 1.8; margin-bottom: 0.85rem;">
                <div><strong>Current role:</strong> {current_role_disp}</div>
                <div><strong>Target:</strong> {target_role_disp}</div>
            </div>
            <div style="background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 8px; padding: 12px 16px; color: #1E40AF; font-size: 0.88rem; margin-bottom: 1rem;">
                {len(skills)} competencies recorded. Target role readiness is evaluated at {analysis['match']}%.
            </div>
            """
        )

        if not skills:
            render_html(
                """
                <div class="ts-callout-blue">
                    Add a few skills to see your career snapshot.
                </div>
                """
            )
            st.markdown("<div style='margin-top: 0.75rem;'></div>", unsafe_allow_html=True)
            if st.button("Add Skills in Portfolio", key="dash_add_skills_btn"):
                navigate_to("Skills & Assessment")
        else:
            df_skills = pd.DataFrame(skills)
            fig_s = px.bar(
                df_skills, x="name", y="years", color="category",
                title="Skills & Experience Duration",
                labels={"name": "", "years": "Years Exp", "category": "Category"},
                color_discrete_map={"Technical": "#2563EB", "Soft Skills": "#10B981", "Domain": "#F59E0B"}
            )
            fig_s.update_layout(
                margin=dict(l=10, r=10, t=35, b=10),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(gridcolor="#F1F5F9", title="Years Exp"),
                xaxis=dict(gridcolor="#F1F5F9", title=""),
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.18, font=dict(size=11, color="#334155"))
            )
            st.plotly_chart(fig_s, use_container_width=True)

    # Personalized Employee Deep Dive: Skills, Assessments, Gaps, Goals, and Performance
    emp_dash_data = get_employee_dashboard_data(uid, emp_id, org_id)
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    tab_ed_roadmap, tab_ed_skills, tab_ed_goals, tab_ed_perf = st.tabs([
        "Career Guidance & Recommendations",
        "Individual Skills & Assessments",
        "Career Goals & Milestones",
        "Performance History"
    ])

    with tab_ed_roadmap:
        c_rm1, c_rm2 = st.columns([1.1, 1], gap="large")
        with c_rm1:
            st.markdown(f"#### Target Role Readiness: **{emp_dash_data['profile'].get('target_role') or 'Choose target role'}**")
            gaps_info = emp_dash_data.get("skill_gaps", {})
            st.metric("Readiness Alignment", f"{gaps_info.get('match_percentage', 0)}%")
            st.progress(gaps_info.get('match_percentage', 0) / 100)

            if gaps_info.get("gaps"):
                st.markdown("##### Priority Competency Recommendations")
                for g in gaps_info["gaps"][:4]:
                    st.write(f"• **{g['skill']}**: Required Level {g['required_level']} (Current: {g['current_level']}) &middot; <span style='color: {'#EF4444' if g['priority']=='High' else '#F59E0B'}; font-weight: 700;'>{g['priority']} Priority</span>", unsafe_allow_html=True)
            if gaps_info.get("recommended_training"):
                st.markdown("##### Suggested Learning Courses")
                for tr_item in gaps_info["recommended_training"][:3]:
                    st.write(f"• **{tr_item}**")

        with c_rm2:
            st.markdown("#### Career Development Tools")
            st.markdown(
                f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                    <div style="font-weight: 800; font-size: 0.98rem; color: #0F172A; margin-bottom: 4px;">{get_svg_icon("reports", size=18, color="#2563EB")} Resume Studio</div>
                    <div style="font-size: 0.85rem; color: #64748B; margin-bottom: 8px;">Export your verified skills, experience, and achievements into an ATS-optimized professional resume.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Open Resume Studio", key="emp_dash_goto_resume", use_container_width=True, type="primary"):
                    navigate_to("Resume Studio")
            with col_b2:
                if st.button("Role Match & Gaps", key="emp_dash_goto_gaps", use_container_width=True):
                    navigate_to("Role Match & Gaps")

    with tab_ed_skills:
        c_esk1, c_esk2 = st.columns([1, 1], gap="large")
        with c_esk1:
            st.markdown("#### Verified Individual Skills")
            indiv_skills = emp_dash_data.get("skills", [])
            if indiv_skills:
                for s_i in indiv_skills:
                    s_name = s_i.get("skill_name") or s_i.get("name") or "Skill"
                    lvl_lbl = s_i.get("proficiency_level") or s_i.get("proficiency") or "Intermediate"
                    lvl_num = {"Beginner": 25, "Intermediate": 50, "Advanced": 75, "Expert": 100}.get(lvl_lbl, 50)
                    s_cat = s_i.get("category") or "Technical"
                    st.write(f"**{s_name}** ({lvl_lbl}) &middot; <span style='font-size:0.8rem; color:#64748B;'>{s_cat}</span>", unsafe_allow_html=True)
                    st.progress(lvl_num / 100)
            else:
                st.info("No individual skills cataloged yet.")
            if st.button("Manage Skills & Competencies", key="emp_dash_manage_sk_btn"):
                navigate_to("Skills & Assessment")

        with c_esk2:
            st.markdown("#### Recent Assessment Evaluations")
            indiv_ass = emp_dash_data.get("assessments", [])
            if indiv_ass:
                ass_records = [
                    {
                        "Capability": a.get("skill_name") or a.get("name") or "Capability Area",
                        "Score (%)": a.get("score") if a.get("score") is not None else (a.get("assessment_score") or 0),
                        "Notes": a.get("notes") or "",
                        "Date": a.get("created_at") or a.get("date") or "",
                    }
                    for a in indiv_ass[:6]
                ]
                df_ia = pd.DataFrame(ass_records)
                st.dataframe(
                    df_ia,
                    width="stretch",
                    hide_index=True,
                    column_config={"Score (%)": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d%%")}
                )
            else:
                st.info("No assessment evaluations logged yet. Record your self-assessment in the Skills module.")

    with tab_ed_goals:
        st.markdown("#### Individual Career Goals & Milestones")
        my_goals = emp_dash_data.get("goals", [])
        if my_goals:
            for g in my_goals:
                p = g.get("progress", 0)
                status = g.get("status", "In Progress")
                status_color = "#10B981" if status == "Completed" else ("#EF4444" if status == "Overdue" else "#3B82F6")
                render_html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <strong style="color: #0F172A; font-size: 0.98rem;">{g['title']}</strong>
                            <span style="font-size: 0.78rem; font-weight: 700; color: {status_color}; background: #F1F5F9; padding: 2px 8px; border-radius: 6px;">{status.upper()}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: #64748B; margin: 4px 0 8px 0;">Due: {g['target_date']} &middot; {g.get('target_designation', 'Growth Milestone')}</div>
                    </div>
                    """
                )
                st.progress(p / 100)
        else:
            st.info("No career milestones defined yet.")
        if st.button("Define New Career Goal", key="emp_dash_new_goal_btn"):
            navigate_to("Career Goals")

    with tab_ed_perf:
        st.markdown("#### Performance Evaluations & Growth Records")
        my_reviews = emp_dash_data.get("reviews", [])
        if my_reviews:
            for r in my_reviews:
                with st.container(border=True):
                    st.write(f"**{r['review_period']}** &middot; Rating: **{r['performance_score']} / 5.0**")
                    if r.get("achievements"):
                        st.caption(f"Achievements: {r['achievements']}")
                    if r.get("manager_feedback"):
                        st.info(f"Manager Feedback: {r['manager_feedback']}")
        else:
            st.info("No performance reviews recorded for your profile yet.")
# ==============================================================================
elif page in ["Employees", "Employee Management"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("employees", size=24, color="#2563EB")} Employees Directory & Management
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Workforce profiles, team assignments, contact information, and skill records.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">ORGANIZATION DIRECTORY</span>
            </div>
        </div>
        """
    )

    tab_dir, tab_add, tab_bulk, tab_edit = st.tabs([
        "Workforce Directory",
        "Add New Employee",
        "Bulk Dataset Upload (CSV/Excel)",
        "Manage Records (Edit / Delete)"
    ])

    # --- TAB 1: WORKFORCE DIRECTORY (PRIMARY VIEW) ---
    with tab_dir:
        c_title, c_toggle = st.columns([2.2, 1.3])
        with c_title:
            st.markdown("#### Workforce Directory & Talent Profiles")
            st.caption("Browse team personnel, filter competencies, and inspect real-time performance ratings.")
        with c_toggle:
            view_mode = st.radio("Display Layout", ["Cards View", "Table View"], horizontal=True, key="emp_view_mode", label_visibility="collapsed")

        f1, f2, f3 = st.columns([2, 1, 1])
        s_query = f1.text_input("Live Search (Name, ID, Role, Skill)", placeholder="Search by name, designation, skill, or ID...", key="emp_live_search")
        s_dept = f2.selectbox("Filter by Department", ["All Departments"] + get_all_departments(org_id=org_id), key="emp_dept_filter")
        s_status = f3.selectbox("Filter by Status", ["All Statuses"] + EMPLOYMENT_STATUSES, key="emp_status_filter")

        emp_results = get_employees(
            search_query=s_query if s_query.strip() else None,
            department_filter=s_dept if s_dept != "All Departments" else None,
            status_filter=s_status if s_status != "All Statuses" else None,
            org_id=org_id
        )

        # Metrics bar with deltas
        m_a, m_b, m_c, m_d = st.columns(4)
        m_a.metric("Matching Personnel", len(emp_results), delta=f"{len(emp_results)} active records")
        m_b.metric("Active Status", sum(1 for e in emp_results if e["employment_status"] == "Active"), delta="In Office / Remote")
        m_c.metric("Avg Experience", f"{round(sum(e['years_experience'] for e in emp_results)/len(emp_results), 1) if emp_results else 0.0} yrs", delta="Tenure")
        avg_rtg_val = round(sum(e['avg_rating'] for e in emp_results if e['avg_rating'])/len([e for e in emp_results if e['avg_rating']]), 2) if any(e['avg_rating'] for e in emp_results) else None
        m_d.metric("Avg Rating", f"{avg_rtg_val} / 5.0" if avg_rtg_val else "N/A", delta="Quarterly Cycle")

        if emp_results:
            if view_mode == "Cards View":
                card_cols = st.columns(3)
                for i, emp in enumerate(emp_results):
                    with card_cols[i % 3]:
                        n_parts = emp["name"].strip().split()
                        init = (n_parts[0][0] + (n_parts[-1][0] if len(n_parts) > 1 else "")).upper()
                        rating_display = f"{emp['avg_rating']} / 5.0" if emp['avg_rating'] else "New Talent"
                        status_cls = "badge-active" if emp['employment_status'] == 'Active' else ('badge-leave' if emp['employment_status'] == 'On Leave' else 'badge-overdue')
                        skills_list = [s.strip() for s in (emp['primary_skills'] or '').split(',') if s.strip()][:4]
                        skills_html = ''.join(f"<span class='skill-pill'>{s}</span>" for s in skills_list) if skills_list else "<span style='font-size: 0.75rem; color: #94A3B8;'>No skills listed</span>"

                        render_html(
                            f"""
                            <div class="talent-card">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div class="talent-avatar-lg">{init}</div>
                                        <div>
                                            <div style="font-weight: 800; font-size: 1.02rem; color: #0F172A; line-height: 1.2;">{emp['name']}</div>
                                            <div style="font-size: 0.8rem; color: #2563EB; font-weight: 600;">{emp['designation']}</div>
                                        </div>
                                    </div>
                                    <span class="badge-status {status_cls}">{emp['employment_status'].upper()}</span>
                                </div>
                                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                                    {get_svg_icon("building", size=13, color="#64748B")} <strong>{emp['department']}</strong> · <span class="tbl-id-pill">{emp['employee_id']}</span>
                                </div>
                                <div class="talent-mini-stats">
                                    <div class="talent-stat-item">
                                        <div class="talent-stat-val">{emp['years_experience']} yrs</div>
                                        <div class="talent-stat-lbl">Experience</div>
                                    </div>
                                    <div class="talent-stat-item">
                                        <div class="talent-stat-val" style="color: #2563EB;">{rating_display}</div>
                                        <div class="talent-stat-lbl">Performance</div>
                                    </div>
                                    <div class="talent-stat-item">
                                        <div class="talent-stat-val">{emp['joining_date']}</div>
                                        <div class="talent-stat-lbl">Joined</div>
                                    </div>
                                </div>
                                <div style="margin-top: 6px;">
                                    <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Core Skills</div>
                                    <div class="talent-skill-pills">{skills_html}</div>
                                </div>
                            </div>
                            """
                        )
                        with st.expander(f"Contact & Profile ({emp['employee_id']})"):
                            st.write(f"**Email:** `{emp['email']}`")
                            st.write(f"**Phone:** `{emp['phone'] or 'Not provided'}`")
                            st.write(f"**Primary Skills:** {emp['primary_skills'] or 'None recorded'}")
            else:
                render_html(render_colored_employee_table(emp_results))
                with st.expander("Spreadsheet Grid View & Raw Data", expanded=False):
                    df_display = pd.DataFrame(emp_results)[["employee_id", "name", "email", "phone", "department", "designation", "joining_date", "employment_status", "years_experience", "primary_skills", "avg_rating"]]
                    df_display.columns = ["ID", "Full Name", "Email", "Phone", "Department", "Designation", "Joined", "Status", "Exp (Yrs)", "Primary Skills", "Performance"]
                    st.dataframe(
                        df_display,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "ID": st.column_config.TextColumn("ID", width="small"),
                            "Full Name": st.column_config.TextColumn("Employee Name", width="medium"),
                            "Department": st.column_config.TextColumn("Department", width="medium"),
                            "Designation": st.column_config.TextColumn("Designation", width="medium"),
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "Exp (Yrs)": st.column_config.NumberColumn("Experience", format="%.1f yrs"),
                            "Performance": st.column_config.ProgressColumn("Score (1–5)", min_value=1.0, max_value=5.0, format="%.2f"),
                        }
                    )

            csv_data = pd.DataFrame(emp_results).to_csv(index=False).encode("utf-8")
            st.download_button(
                "Export Filtered Directory (CSV)",
                csv_data,
                "talent_growth_workforce_directory.csv",
                "text/csv",
                type="primary"
            )
        else:
            st.info("No employee records found matching your search and filter criteria.")

    # --- TAB 2: ADD EMPLOYEE ---
    with tab_add:
        st.markdown("#### Register New Employee")
        st.caption("Enter employee credentials and core competencies. Fields marked with (*) are required.")

        if st.session_state.clear_emp_form_flag:
            st.session_state.e_name = ""
            st.session_state.e_id = ""
            st.session_state.e_email = ""
            st.session_state.e_phone = ""
            st.session_state.e_dept = "Select Department"
            st.session_state.e_desig = ""
            st.session_state.e_exp = 0.0
            st.session_state.e_skills = ""
            st.session_state.e_status = "Active"
            st.session_state.clear_emp_form_flag = False

        depts = ["Select Department"] + get_all_departments()

        col_form_wrap, col_guidelines = st.columns([2, 1])
        with col_form_wrap:
            with st.form("add_employee_master_form", clear_on_submit=False):
                name_input = st.text_input("Employee Full Name *", key="e_name", placeholder="e.g. Alexander Wright")
                id_input = st.text_input("Employee ID Code *", key="e_id", placeholder="e.g. EMP205").strip().upper()
                email_input = st.text_input("Corporate Email Address", key="e_email", placeholder="e.g. alexander.w@company.com")
                phone_input = st.text_input("Contact Phone Number", key="e_phone", placeholder="+1-555-0199")

                c_d1, c_d2 = st.columns(2)
                dept_input = c_d1.selectbox("Department *", depts, key="e_dept")
                desig_input = c_d2.text_input("Designation / Title *", key="e_desig", placeholder="e.g. Senior Backend Engineer")

                c_e1, c_e2, c_e3 = st.columns(3)
                exp_input = c_e1.number_input("Years of Experience *", min_value=0.0, max_value=60.0, value=0.0, step=0.5, key="e_exp")
                status_input = c_e2.selectbox("Employment Status", EMPLOYMENT_STATUSES, key="e_status")
                join_input = c_e3.date_input("Joining Date", value=date.today())

                skills_input = st.text_input("Primary Skills (Comma-separated) *", key="e_skills", placeholder="e.g. Python, Django, PostgreSQL, Docker, AWS")

                submit_add_emp = st.form_submit_button("Save Employee Record to Database", type="primary", use_container_width=True)

            if st.button("Reset Form Fields", use_container_width=True):
                st.session_state.clear_emp_form_flag = True
                st.rerun()

            if submit_add_emp:
                if not name_input.strip():
                    st.error("Validation Error: Employee Name is mandatory.")
                elif not id_input.strip():
                    st.error("Validation Error: Employee ID Code is mandatory.")
                elif dept_input == "Select Department" or not dept_input.strip():
                    st.error("Validation Error: Please select a valid Department.")
                elif not desig_input.strip():
                    st.error("Validation Error: Designation is mandatory.")
                elif not skills_input.strip():
                    st.error("Validation Error: Primary Skills are mandatory.")
                elif exp_input < 0:
                    st.error("Validation Error: Experience cannot be negative.")
                else:
                    success, msg = add_employee(
                        employee_id=id_input,
                        name=name_input,
                        department=dept_input,
                        designation=desig_input,
                        years_experience=exp_input,
                        primary_skills=skills_input,
                        email=email_input if email_input.strip() else None,
                        phone=phone_input,
                        joining_date=join_input.isoformat(),
                        employment_status=status_input,
                        created_by=uid,
                        org_id=org_id
                    )
                    if success:
                        st.success(msg)
                        st.session_state.clear_emp_form_flag = True
                        st.rerun()
                    else:
                        st.error(msg)

        with col_guidelines:
            with st.container(border=True):
                st.markdown("#### System Validation Rules")
                st.markdown(
                    """
                    - **Unique Constraints**: Employee ID and Corporate Email must be unique across the organization.
                    - **Experience Boundary**: Accepted values range between `0.0` and `60.0` years.
                    - **Competency Catalog**: Primary skills are parsed and indexed into the organizational skills index.
                    - **Persistence Guarantee**: Saved directly into SQLite with parameterized queries.
                    """
                )

    # --- TAB 2: BULK DATASET UPLOAD ---
    with tab_bulk:
        st.markdown("#### Bulk Employee Dataset Ingestion")
        st.caption("Upload a formatted CSV or Excel file containing multiple employee records for instant batch ingestion into SQLite.")

        col_b_left, col_b_right = st.columns([2, 1])
        with col_b_right:
            with st.container(border=True):
                st.markdown("##### Standard CSV Template")
                st.markdown("Download our official pre-structured employee dataset template to ensure error-free imports.")
                sample_csv_str = get_sample_employee_csv()
                st.download_button(
                    "Download Sample CSV Template",
                    data=sample_csv_str,
                    file_name="talent_growth_sample_employees.csv",
                    mime="text/csv",
                    type="secondary",
                    use_container_width=True
                )
                st.markdown(
                    """
                    <div style="font-size: 0.8rem; color: #64748B; margin-top: 10px;">
                        <strong>Supported Columns:</strong><br>
                        • <code>employee_id</code> (Unique, required)<br>
                        • <code>name</code> (Full name, required)<br>
                        • <code>department</code> (Business unit)<br>
                        • <code>designation</code> (Job role)<br>
                        • <code>primary_skills</code> (Comma-separated)<br>
                        • <code>years_experience</code> (0–60)<br>
                        • <code>email</code>, <code>phone</code>, <code>joining_date</code>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col_b_left:
            uploaded_file = st.file_uploader(
                "Select CSV or Excel Dataset to Ingest",
                type=["csv", "xlsx"],
                help="Accepts .csv or .xlsx spreadsheets containing multiple employee profiles."
            )

            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df_upload = pd.read_csv(uploaded_file)
                    else:
                        df_upload = pd.read_excel(uploaded_file)

                    st.markdown(f"##### Dataset Preview ({len(df_upload)} rows detected)")
                    st.dataframe(df_upload.head(10), width="stretch", hide_index=True)

                    btn_import = st.button("Validate & Ingest Dataset into Database", type="primary", use_container_width=True)

                    if btn_import:
                        with st.spinner("Processing records and enforcing SQLite constraints..."):
                            import_res = bulk_import_employees_df(df_upload, created_by=uid, org_id=org_id)

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total In File", import_res["total"])
                        m2.metric("Successfully Added", import_res["success_count"])
                        m3.metric("Skipped / Duplicate", import_res["skipped_count"])

                        if import_res["success_count"] > 0:
                            st.success(f"Successfully imported {import_res['success_count']} employees into {org_name}!")

                        if import_res["errors"]:
                            with st.expander(f"Review Ingestion Notices & Skipped Records ({len(import_res['errors'])})", expanded=True):
                                for err_msg in import_res["errors"]:
                                    st.warning(err_msg)

                        if import_res["success_count"] > 0:
                            st.rerun()

                except Exception as ex:
                    st.error(f"Error reading dataset file: {ex}")
            else:
                st.info("Upload a CSV or Excel dataset above to begin bulk employee ingestion.")

    # --- TAB 4: EDIT & DELETE ---
    with tab_edit:
        st.markdown("#### Modify or Remove Employee Records")
        all_emps = get_employees(org_id=org_id)
        if not all_emps:
            st.info(f"No employee records currently available in {org_name}.")
        else:
            emp_map = {f"{e['employee_id']} — {e['name']} ({e['designation']})": e['employee_id'] for e in all_emps}
            selected_emp_k = st.selectbox("Select Employee Record", list(emp_map.keys()))
            selected_emp_code = emp_map[selected_emp_k]
            emp_curr = get_employee_by_id(selected_emp_code, org_id=org_id)

            if emp_curr:
                col_ed, col_rm = st.columns([1.6, 1])
                with col_ed:
                    with st.form("edit_emp_master_form"):
                        st.markdown(f"##### Edit Details for `{emp_curr['employee_id']}`")
                        up_name = st.text_input("Full Legal Name", value=emp_curr["name"])
                        up_email = st.text_input("Corporate Email", value=emp_curr["email"] or "")
                        up_phone = st.text_input("Phone Number", value=emp_curr["phone"] or "")

                        d_list = get_all_departments(org_id=org_id)
                        d_idx = d_list.index(emp_curr["department"]) if emp_curr["department"] in d_list else 0
                        up_dept = st.selectbox("Department", d_list, index=d_idx)
                        up_desig = st.text_input("Designation / Title", value=emp_curr["designation"])

                        s_idx = EMPLOYMENT_STATUSES.index(emp_curr["employment_status"]) if emp_curr["employment_status"] in EMPLOYMENT_STATUSES else 0
                        up_status = st.selectbox("Employment Status", EMPLOYMENT_STATUSES, index=s_idx)
                        up_exp = st.number_input("Years of Experience", min_value=0.0, max_value=60.0, value=float(emp_curr["years_experience"]), step=0.5)
                        up_skills = st.text_input("Primary Skills", value=emp_curr["primary_skills"])

                        update_save_btn = st.form_submit_button("Update Employee Record", type="primary")

                    if update_save_btn:
                        ok_upd, msg_upd = update_employee(
                            employee_id=emp_curr["employee_id"],
                            name=up_name,
                            department=up_dept,
                            designation=up_desig,
                            years_experience=up_exp,
                            primary_skills=up_skills,
                            email=up_email if up_email.strip() else None,
                            phone=up_phone,
                            joining_date=emp_curr["joining_date"],
                            employment_status=up_status,
                            org_id=org_id
                        )
                        if ok_upd:
                            st.success(msg_upd)
                            st.rerun()
                        else:
                            st.error(msg_upd)

                with col_rm:
                    with st.container(border=True):
                        st.markdown("##### Remove Employee Record")
                        st.markdown(
                            f"""
                            <div style="font-size: 0.88rem; color: #475569; margin-bottom: 8px;">
                                Permanently delete <strong>{emp_curr['name']}</strong> (<code>{emp_curr['employee_id']}</code>)?
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.caption("Cascade removes associated reviews, skills, and training logs.")
                        confirm_deletion = st.checkbox("I confirm deletion of this record.")
                        if st.button("Permanently Delete", type="secondary", disabled=not confirm_deletion):
                            ok_del, msg_del = delete_employee(emp_curr["employee_id"], org_id=org_id)
                            if ok_del:
                                st.success(msg_del)
                                st.rerun()
                            else:
                                st.error(msg_del)

# ==============================================================================
# 4. PERFORMANCE REVIEWS & EVALUATIONS
# ==============================================================================
elif page in ["Performance", "Performance Reviews", "My Performance Reviews"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("performance", size=24, color="#8B5CF6")} Performance Evaluations & Trends
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Structured review cycles, quantitative ratings (1.0–5.0), and performance trajectory analytics.
                </div>
            </div>
            <div>
                <span class="badge-status badge-completed">PERFORMANCE INTELLIGENCE</span>
            </div>
        </div>
        """
    )

    if is_admin:
        tab_rev_list, tab_rev_add, tab_rev_trends = st.tabs(["Evaluation Records", "Record New Evaluation", "Distribution Analytics"])

        with tab_rev_list:
            all_reviews = get_performance_reviews(org_id=org_id)
            if all_reviews:
                c_head1, c_head2 = st.columns([2.2, 1.3])
                with c_head1:
                    st.markdown("#### Performance Review Records & Highlights")
                    st.caption("Quantitative evaluations (1.0 - 5.0), achievement highlights, and manager feedback.")
                with c_head2:
                    rev_view_mode = st.radio("Review Layout", ["Cards View", "Table View"], horizontal=True, key="rev_layout_mode", label_visibility="collapsed")

                # Filter by rating tier
                c_rf1, c_rf2 = st.columns([2, 1.5])
                rating_filter = c_rf1.selectbox("Filter by Performance Tier", ["All Evaluations", "Top Performers (4.5–5.0)", "Exceeds Expectations (4.0–4.4)", "Meets Expectations (3.0–3.9)", "Needs Development (< 3.0)"], key="rev_tier_filter")

                filtered_reviews = all_reviews
                if rating_filter == "Top Performers (4.5–5.0)":
                    filtered_reviews = [r for r in all_reviews if r["performance_score"] >= 4.5]
                elif rating_filter == "Exceeds Expectations (4.0–4.4)":
                    filtered_reviews = [r for r in all_reviews if 4.0 <= r["performance_score"] < 4.5]
                elif rating_filter == "Meets Expectations (3.0–3.9)":
                    filtered_reviews = [r for r in all_reviews if 3.0 <= r["performance_score"] < 4.0]
                elif rating_filter == "Needs Development (< 3.0)":
                    filtered_reviews = [r for r in all_reviews if r["performance_score"] < 3.0]

                if rev_view_mode == "Cards View":
                    for r in filtered_reviews:
                        score = r["performance_score"]
                        tier_label = "TOP PERFORMER" if score >= 4.5 else ("EXCEEDS GOALS" if score >= 4.0 else "MEETS STANDARDS")
                        render_html(
                            f"""
                            <div class="review-card-item">
                                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                    <div>
                                        <span style="font-weight: 800; font-size: 1.08rem; color: #0F172A;">{r['employee_name']}</span>
                                        <span style="font-size: 0.8rem; color: #64748B; margin-left: 8px;">({r['department']} · {r['designation']})</span>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span class="badge-status badge-progress">{r['review_period']}</span>
                                        <span class="tbl-rating-pill">{score} / 5.0 · {tier_label}</span>
                                    </div>
                                </div>
                                <div class="quote-box">
                                    "{r['achievements'] or 'Demonstrated strong commitment to team outcomes and technical delivery.'}"
                                </div>
                                <div style="display: flex; gap: 14px; margin-top: 10px; font-size: 0.84rem;">
                                    <div style="flex: 1;">
                                        <strong style="color: #065F46;">Strengths:</strong>
                                        <span style="color: #334155;"> {r['strengths'] or 'Consistency, technical proficiency'}</span>
                                    </div>
                                    <div style="flex: 1;">
                                        <strong style="color: #9A3412;">Growth Areas:</strong>
                                        <span style="color: #334155;"> {r['improvements'] or 'Leadership and cross-team alignment'}</span>
                                    </div>
                                </div>
                                {f'<div style="margin-top: 8px; font-size: 0.82rem; color: #475569;"><strong>Manager Feedback:</strong> {r["manager_feedback"]}</div>' if r.get('manager_feedback') else ''}
                            </div>
                            """
                        )
                else:
                    render_html(render_colored_review_table(filtered_reviews))
                    with st.expander("Spreadsheet Grid View & Raw Data", expanded=False):
                        df_rev = pd.DataFrame(filtered_reviews)[["employee_id", "employee_name", "department", "designation", "review_period", "performance_score", "achievements", "strengths", "improvements", "manager_feedback", "created_at"]]
                        df_rev.columns = ["Emp ID", "Employee Name", "Department", "Designation", "Period", "Score (1–5)", "Key Achievements", "Demonstrated Strengths", "Growth Areas", "Manager Feedback", "Recorded On"]
                        st.dataframe(
                            df_rev,
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "Emp ID": st.column_config.TextColumn("ID", width="small"),
                                "Employee Name": st.column_config.TextColumn("Employee", width="medium"),
                                "Department": st.column_config.TextColumn("Department", width="medium"),
                                "Period": st.column_config.TextColumn("Review Period", width="small"),
                                "Score (1–5)": st.column_config.ProgressColumn("Performance Score", min_value=1.0, max_value=5.0, format="%.2f"),
                                "Recorded On": st.column_config.DateColumn("Evaluation Date", format="YYYY-MM-DD")
                            }
                        )

                # Performance Trajectory Chart
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                st.markdown("#### Performance Evaluation Trajectory")
                df_trend = pd.DataFrame(all_reviews)
                if not df_trend.empty and "review_period" in df_trend.columns:
                    trend_agg = df_trend.groupby("review_period")["performance_score"].mean().reset_index()
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=trend_agg["review_period"],
                        y=trend_agg["performance_score"],
                        mode="lines+markers",
                        line=dict(color="#2563EB", width=3, shape="spline"),
                        marker=dict(size=8, color="#1D4ED8", line=dict(width=2, color="#FFFFFF")),
                        fill="tozeroy",
                        fillcolor="rgba(37, 99, 235, 0.08)",
                        name="Workforce Avg"
                    ))
                    fig_trend.update_layout(
                        height=260,
                        margin=dict(l=10, r=10, t=10, b=10),
                        yaxis=dict(range=[1.0, 5.0], gridcolor="#F1F5F9"),
                        xaxis=dict(gridcolor="#F1F5F9"),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF"
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No performance evaluations recorded yet.")

        with tab_rev_add:
            st.markdown("#### Record Performance Evaluation")
            emps = get_employees(org_id=org_id)
            if not emps:
                st.warning("Please add employees first in Employee Management.")
            else:
                emp_choices = {f"{e['employee_id']} — {e['name']} ({e['designation']})": e['employee_id'] for e in emps}
                with st.form("add_review_form"):
                    chosen_emp = st.selectbox("Select Employee *", list(emp_choices.keys()))
                    rev_period = st.text_input("Review Period *", placeholder="e.g. Q1 2026 or 2025 Annual Review")
                    rev_score = st.slider("Performance Rating (1.0 = Needs Improvement, 5.0 = Exceptional) *", min_value=1.0, max_value=5.0, value=4.0, step=0.1)
                    achieve = st.text_area("Key Achievements & Deliverables", placeholder="Projects completed, measurable impact, KPI results...")
                    strengths_txt = st.text_area("Demonstrated Core Strengths", placeholder="Competencies, leadership, teamwork...")
                    improve_txt = st.text_area("Areas for Growth & Upskilling", placeholder="Skills to develop, training needs...")
                    feedback_txt = st.text_area("Executive Feedback & Summary Notes", placeholder="Overall evaluation summary and next steps...")

                    save_rev_btn = st.form_submit_button("Save Performance Evaluation", type="primary")

                if save_rev_btn:
                    if not rev_period.strip():
                        st.error("Validation Error: Review Period is required.")
                    else:
                        ok_r, msg_r = add_performance_review(
                            employee_id=emp_choices[chosen_emp],
                            review_period=rev_period,
                            performance_score=rev_score,
                            achievements=achieve,
                            strengths=strengths_txt,
                            improvements=improve_txt,
                            manager_feedback=feedback_txt,
                            reviewer_id=uid,
                            org_id=org_id
                        )
                        if ok_r:
                            st.success(msg_r)
                            st.rerun()
                        else:
                            st.error(msg_r)

        with tab_rev_trends:
            st.markdown("#### Workforce Performance Rating Distribution")
            all_revs = get_performance_reviews(org_id=org_id)
            if all_revs:
                df_r = pd.DataFrame(all_revs)
                fig_hist = px.histogram(
                    df_r, x="performance_score", nbins=10,
                    title="Distribution of Ratings across Workforce",
                    labels={"performance_score": "Rating (1.0 - 5.0)", "count": "Count"},
                    color_discrete_sequence=["#2563EB"]
                )
                fig_hist.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=320)
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No evaluation data available to chart.")
    else:
        my_revs = get_performance_reviews(employee_id=emp_id, org_id=org_id)
        st.markdown(f"#### Evaluation History for Employee ({emp_id})")
        if my_revs:
            avg_my = round(sum(r["performance_score"] for r in my_revs) / len(my_revs), 2)
            st.metric("Your Average Performance Rating", f"{avg_my} / 5.0")
            for r in my_revs:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                            <strong style="font-size: 1.05rem; color: #0F172A;">{r['review_period']}</strong>
                            <span class="badge-status badge-progress" style="font-size: 0.9rem;">Rating: {r['performance_score']} / 5.0</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if r.get("achievements"):
                        st.write(f"**Key Achievements:** {r['achievements']}")
                    if r.get("strengths"):
                        st.write(f"**Recognized Strengths:** {r['strengths']}")
                    if r.get("improvements"):
                        st.write(f"**Growth Opportunities:** {r['improvements']}")
                    if r.get("manager_feedback"):
                        st.info(f"**Executive Feedback:** {r['manager_feedback']}")
        else:
            st.info("No performance evaluations recorded for your profile yet.")

# ==============================================================================
# 5. SKILLS & COMPETENCY MATRIX / SKILLS & ASSESSMENTS
# ==============================================================================
elif page in ["Skills & Assessment", "Skills and assessments", "Skills", "Skills & Competency Matrix", "Skills & Assessments"]:
    if not is_admin:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div>
                    <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                        {get_svg_icon("skills", size=24, color="#10B981")} My Skills & Assessment Center
                    </div>
                    <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                        Manage your verified competencies, track assessment history, and analyze role benchmark readiness.
                    </div>
                </div>
                <div>
                    <span class="badge-status badge-active">{emp_id} &middot; {org_name}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_emp_skills, tab_emp_assessments, tab_emp_gaps = st.tabs([
            "My Competencies & Skills",
            "Skill Assessments & History",
            "My Skill-Gap Analysis"
        ])

        with tab_emp_skills:
            st.markdown("#### Add or Update Verified Competency")
            with st.form("add_inline_skill_form"):
                c_s1, c_s2, c_s3, c_s4 = st.columns([3, 2, 2, 1.5])
                with c_s1:
                    new_sk_name = st.text_input("Skill Name *", placeholder="e.g. Python, SQL, Communication, Leadership, Data Analysis")
                with c_s2:
                    new_sk_cat = st.selectbox("Category", ["Technical", "Soft Skill", "Leadership", "Tools", "Domain", "Business"])
                with c_s3:
                    new_sk_prof = st.selectbox("Proficiency Level", list(LEVELS.keys()))
                with c_s4:
                    new_sk_yrs = st.number_input("Years Experience", min_value=0.0, max_value=50.0, value=1.0, step=0.5, format="%.1f")

                btn_add_sk = st.form_submit_button("Save Competency", type="primary")

            if btn_add_sk:
                if new_sk_name.strip():
                    ok_sk, msg_sk = add_employee_skill(
                        emp_id if emp_id else f"EMP-{uid}",
                        new_sk_name.strip(),
                        new_sk_prof,
                        new_sk_cat,
                        new_sk_yrs,
                        org_id=org_id,
                        user_id=uid
                    )
                    add_skill(uid, new_sk_name.strip(), new_sk_cat, new_sk_prof, new_sk_yrs)
                    if ok_sk:
                        st.success(f"Added competency '{new_sk_name.strip()}' successfully!")
                        st.rerun()
                    else:
                        st.error(msg_sk)
                else:
                    st.error("Please enter a skill name.")

            user_emp_skills = get_employee_skills(emp_id if emp_id else f"EMP-{uid}", org_id=org_id)
            if user_emp_skills:
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                st.markdown(f"#### Verified Skills Profile ({len(user_emp_skills)} Competencies)")
                render_html(render_colored_skills_table(user_emp_skills))

                # Visual Proficiency Progress Bars for Individual Skills
                st.markdown("##### Skill Proficiency Levels")
                p_cols = st.columns(2)
                for i, s_item in enumerate(user_emp_skills):
                    col_target = p_cols[i % 2]
                    lvl_label = s_item.get("proficiency_level") or s_item.get("proficiency") or "Intermediate"
                    lvl_pct = {"Beginner": 25, "Intermediate": 50, "Advanced": 75, "Expert": 100}.get(lvl_label, 50)
                    s_name = s_item.get("skill_name") or s_item.get("name") or "Skill"
                    s_cat = s_item.get("category") or "Technical"
                    with col_target:
                        st.write(f"**{s_name}** &middot; <span style='font-size:0.8rem; color:#64748B;'>{s_cat} ({lvl_label} — {lvl_pct}%)</span>", unsafe_allow_html=True)
                        st.progress(lvl_pct / 100)

                col_d1, col_d2 = st.columns([3, 1])
                with col_d1:
                    sk_del_map = {f"{s.get('skill_name') or s.get('name') or 'Skill'} ({s.get('proficiency_level') or s.get('proficiency') or 'Intermediate'})": s.get("id") for s in user_emp_skills}
                    sel_del_sk = st.selectbox("Select skill to remove", ["Choose a skill to delete..."] + list(sk_del_map.keys()))
                with col_d2:
                    st.write("")
                    st.write("")
                    if sel_del_sk != "Choose a skill to delete..." and st.button("Delete Skill", type="secondary"):
                        delete_employee_skill(sk_del_map[sel_del_sk], employee_id=emp_id, org_id=org_id)
                        delete_skill(uid, sk_del_map[sel_del_sk])
                        st.success("Skill removed.")
                        st.rerun()
            else:
                st.info("No skills cataloged yet. Add your competencies above.")

        with tab_emp_assessments:
            st.markdown("#### Record Skill Assessment")
            st.caption("Perform a self-evaluation on key capabilities or review your verified assessment score history.")

            c_as1, c_as2 = st.columns([1.1, 1], gap="large")
            with c_as1:
                with st.form("emp_rec_assessment_form"):
                    cap_areas = ["Python", "SQL", "Communication", "Leadership", "Data Analysis", "System Design", "Problem Solving", "Project Management", "Domain Knowledge", "Cloud Architecture"]
                    cap_area = st.selectbox("Capability / Skill Area *", cap_areas)
                    conf_score = st.slider("Evaluated Proficiency / Confidence Score (0–100%) *", min_value=0, max_value=100, value=75, step=5)
                    ass_notes = st.text_area("Assessment Evidence & Key Deliverables", placeholder="Describe practical experience, projects, or certifications supporting this assessment...")
                    btn_save_ass = st.form_submit_button("Record Assessment to Profile", type="primary")

                if btn_save_ass:
                    ok_ass = add_assessment(
                        uid=uid,
                        category=cap_area,
                        score=float(conf_score),
                        employee_id=emp_id,
                        org_id=org_id,
                        skill_name=cap_area,
                        notes=ass_notes
                    )
                    if ok_ass:
                        st.success(f"Assessment recorded for {cap_area} ({conf_score}%) successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to record assessment. Please try again.")

            with c_as2:
                prev_assessments = get_assessments(uid=uid, employee_id=emp_id, org_id=org_id)
                st.markdown(f"#### Individual Assessment Results ({len(prev_assessments)})")
                if prev_assessments:
                    # Spider/Radar or Bar Chart of Assessments
                    chart_skills = [a.get("skill_name") or a.get("category") for a in prev_assessments[:8]]
                    chart_scores = [a.get("score", 0.0) for a in prev_assessments[:8]]
                    
                    if len(chart_skills) >= 3:
                        fig_ass = go.Figure()
                        fig_ass.add_trace(go.Scatterpolar(
                            r=chart_scores + [chart_scores[0]],
                            theta=chart_skills + [chart_skills[0]],
                            fill='toself',
                            fillcolor='rgba(16, 185, 129, 0.15)',
                            line=dict(color='#10B981', width=2),
                            name='Assessment Score'
                        ))
                        fig_ass.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                            showlegend=False,
                            height=270,
                            margin=dict(l=25, r=25, t=25, b=25),
                            paper_bgcolor="#FFFFFF"
                        )
                        st.plotly_chart(fig_ass, use_container_width=True)
                    else:
                        df_ass_chart = pd.DataFrame({"Capability": chart_skills, "Score": chart_scores})
                        fig_bar_ass = px.bar(df_ass_chart, x="Capability", y="Score", range_y=[0, 100], color_discrete_sequence=["#10B981"])
                        fig_bar_ass.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_bar_ass, use_container_width=True)
                else:
                    st.info("No assessment scores logged yet. Complete the form to start your assessment baseline.")

            # Full Assessment Log Table
            if prev_assessments:
                st.markdown("##### Assessment History Log")
                ass_log_records = [
                    {
                        "Skill / Capability": a.get("skill_name") or a.get("name") or "Capability Area",
                        "Score (%)": a.get("score") if a.get("score") is not None else (a.get("assessment_score") or 0),
                        "Notes / Evidence": a.get("notes") or "",
                        "Evaluation Date": a.get("created_at") or a.get("date") or "",
                    }
                    for a in prev_assessments
                ]
                df_ass_log = pd.DataFrame(ass_log_records)
                st.dataframe(
                    df_ass_log,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Skill / Capability": st.column_config.TextColumn("Capability Area", width="medium"),
                        "Score (%)": st.column_config.ProgressColumn("Assessment Score", min_value=0, max_value=100, format="%d%%"),
                        "Notes / Evidence": st.column_config.TextColumn("Notes / Feedback", width="large"),
                        "Evaluation Date": st.column_config.DateColumn("Recorded On", format="YYYY-MM-DD")
                    }
                )

        with tab_emp_gaps:
            st.markdown("#### Individual Skill-Gap Analysis & Benchmark Readiness")
            all_roles = list(ROLE_CATALOG.keys())
            def_idx = all_roles.index(profile["target_role"]) if profile.get("target_role") in all_roles else 0
            target_role_eval = st.selectbox("Select Target Role for Gap Analysis", all_roles, index=def_idx, key="emp_sel_bench_role")

            gap_result = get_employee_skill_gaps(emp_id if emp_id else f"EMP-{uid}", target_role_eval, org_id=org_id)
            c_g1, c_g2 = st.columns([1.1, 1], gap="large")
            with c_g1:
                st.metric(f"Match Readiness for {target_role_eval}", f"{gap_result['match_percentage']}%", delta=f"{gap_result['match_percentage']}% Target Alignment")
                st.progress(gap_result['match_percentage'] / 100)

                if gap_result["gaps"]:
                    top_gaps = gap_result["gaps"][:6]
                    cat_names = [g["skill"] for g in top_gaps]
                    c_vals = [g["current_level"] for g in top_gaps]
                    r_vals = [g["required_level"] for g in top_gaps]

                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(
                        r=c_vals + [c_vals[0]],
                        theta=cat_names + [cat_names[0]],
                        fill='toself',
                        fillcolor='rgba(37, 99, 235, 0.15)',
                        name='Current Level',
                        line=dict(color='#2563EB', width=2)
                    ))
                    fig_radar.add_trace(go.Scatterpolar(
                        r=r_vals + [r_vals[0]],
                        theta=cat_names + [cat_names[0]],
                        fill='toself',
                        fillcolor='rgba(16, 185, 129, 0.10)',
                        name='Target Benchmark',
                        line=dict(color='#10B981', width=2, dash='dot')
                    ))
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3, 4], ticktext=['Beg', 'Int', 'Adv', 'Exp'])
                        ),
                        showlegend=True,
                        height=280,
                        margin=dict(l=25, r=25, t=25, b=25),
                        paper_bgcolor="#FFFFFF"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

            with c_g2:
                st.markdown(f"**Benchmark Role Standard:**")
                st.info(f"{gap_result['criteria']}")

                if gap_result["gaps"]:
                    st.markdown("##### Priority Development Areas")
                    levels_str = {0: "None (0)", 1: "Beginner (1)", 2: "Intermediate (2)", 3: "Advanced (3)", 4: "Expert (4)"}
                    render_html(render_colored_gaps_table(gap_result["gaps"], levels_str))

                if gap_result.get("recommended_training"):
                    st.markdown("##### Recommended Targeted Training Courses")
                    for t_item in gap_result["recommended_training"]:
                        st.markdown(f"• **{t_item}** — Focus program to close competency gaps.")
    else:
        # Admin View with Full Organization Competency Matrix Tabs
        render_html(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div>
                    <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                        {get_svg_icon("skills", size=24, color="#10B981")} Skills Management & Organization Assessments
                    </div>
                    <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                        Manage employee competencies, record formal skills assessments, and track role gap analytics for {org_name}.
                    </div>
                </div>
                <div>
                    <span class="badge-status badge-active">{org_id}</span>
                </div>
            </div>
            """
        )

        tab_sk_matrix, tab_sk_assessments, tab_sk_gaps, tab_sk_train = st.tabs([
            "Skills Portfolio",
            "Assessments & Evaluations",
            "Role Gap Analysis",
            "Training & Upskilling"
        ])

        all_emps = get_employees(org_id=org_id)
        if all_emps:
            emp_sk_map = {f"{e['employee_id']} — {e['name']} ({e['designation']})": e['employee_id'] for e in all_emps}
        else:
            emp_sk_map = {}

        with tab_sk_matrix:
            if not emp_sk_map:
                st.warning(f"No employees found in organization {org_id}. Please register or add employees first.")
            else:
                selected_sk_emp = st.selectbox("Select Employee Profile", list(emp_sk_map.keys()), key="hr_sel_sk_emp")
                target_code = emp_sk_map[selected_sk_emp]

                col_sk_form, col_sk_table = st.columns([1, 1.5])
                with col_sk_form:
                    with st.form("add_sk_form"):
                        st.markdown(f"##### Add Competency for `{target_code}`")
                        sk_name = st.text_input("Skill Name *", placeholder="e.g. Python, SQL, Docker, React, AWS")
                        sk_cat = st.selectbox("Skill Category", ["Technical", "Domain", "Soft Skill", "Leadership", "Tool", "Business"])
                        sk_prof = st.selectbox("Proficiency Level", list(LEVELS.keys()))
                        sk_yrs = st.number_input("Years Experience", min_value=0.0, max_value=50.0, value=1.5, step=0.5)
                        submit_sk = st.form_submit_button("Add Skill to Portfolio", type="primary")

                    if submit_sk:
                        ok_sk, msg_sk = add_employee_skill(target_code, sk_name, sk_prof, sk_cat, sk_yrs, org_id=org_id)
                        if ok_sk:
                            st.success(msg_sk)
                            st.rerun()
                        else:
                            st.error(msg_sk)

                with col_sk_table:
                    emp_skills = get_employee_skills(target_code, org_id=org_id)
                    st.markdown(f"##### Verified Skills Catalog ({len(emp_skills)})")
                    if emp_skills:
                        render_html(render_colored_skills_table(emp_skills))
                        sk_del_map = {f"{s.get('skill_name') or s.get('name') or 'Skill'} ({s.get('proficiency_level') or s.get('proficiency') or 'Intermediate'})": s.get("id") for s in emp_skills}
                        sel_del_sk = st.selectbox("Remove Competency", ["Select skill to remove..."] + list(sk_del_map.keys()), key="hr_del_sk_sel")
                        if sel_del_sk != "Select skill to remove..." and st.button("Delete Skill", key="hr_del_sk_btn"):
                            delete_employee_skill(sk_del_map[sel_del_sk], employee_id=target_code, org_id=org_id)
                            st.success("Skill removed successfully.")
                            st.rerun()
                    else:
                        st.info("No skills cataloged for this employee profile yet.")

        with tab_sk_assessments:
            st.markdown("#### HR Skills Assessment & Capability Evaluation")
            st.caption("Record formal skills evaluations and monitor assessment score history for employees in your organization.")

            if not emp_sk_map:
                st.warning("No employees available to evaluate.")
            else:
                sel_ass_emp = st.selectbox("Select Employee to Assess", list(emp_sk_map.keys()), key="hr_sel_ass_emp")
                target_ass_code = emp_sk_map[sel_ass_emp]

                c_haf1, c_haf2 = st.columns([1.1, 1], gap="large")
                with c_haf1:
                    with st.form("hr_rec_assessment_form"):
                        st.markdown(f"##### Record Assessment for `{target_ass_code}`")
                        hr_cap_areas = ["Python", "SQL", "Communication", "Leadership", "Data Analysis", "System Design", "Problem Solving", "Project Management", "Domain Knowledge", "Cloud Architecture"]
                        hr_cap_area = st.selectbox("Capability / Competency *", hr_cap_areas, key="hr_ass_cap")
                        hr_conf_score = st.slider("Assessment Score (0–100%) *", min_value=0, max_value=100, value=80, step=5, key="hr_ass_score")
                        hr_ass_notes = st.text_area("HR / Manager Evaluation Notes", placeholder="Demonstrated skills in recent sprint, code review scores, technical proficiency...", key="hr_ass_notes")
                        btn_hr_ass = st.form_submit_button("Submit Assessment Record", type="primary")

                    if btn_hr_ass:
                        ok_hr_ass = add_assessment(
                            category=hr_cap_area,
                            score=float(hr_conf_score),
                            employee_id=target_ass_code,
                            org_id=org_id,
                            skill_name=hr_cap_area,
                            notes=hr_ass_notes
                        )
                        if ok_hr_ass:
                            st.success(f"Assessment score of {hr_conf_score}% recorded for {target_ass_code} ({hr_cap_area})!")
                            st.rerun()
                        else:
                            st.error("Failed to record assessment.")

                with c_haf2:
                    hr_emp_ass = get_assessments(employee_id=target_ass_code, org_id=org_id)
                    st.markdown(f"##### Assessment Trajectory for `{target_ass_code}` ({len(hr_emp_ass)})")
                    if hr_emp_ass:
                        chart_skills = [a.get("skill_name") or a.get("category") for a in hr_emp_ass[:8]]
                        chart_scores = [a.get("score", 0.0) for a in hr_emp_ass[:8]]
                        if len(chart_skills) >= 3:
                            fig_hr_ass = go.Figure()
                            fig_hr_ass.add_trace(go.Scatterpolar(
                                r=chart_scores + [chart_scores[0]],
                                theta=chart_skills + [chart_skills[0]],
                                fill='toself',
                                fillcolor='rgba(16, 185, 129, 0.15)',
                                line=dict(color='#10B981', width=2),
                                name='Assessment Score'
                            ))
                            fig_hr_ass.update_layout(
                                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                showlegend=False,
                                height=270,
                                margin=dict(l=25, r=25, t=25, b=25),
                                paper_bgcolor="#FFFFFF"
                            )
                            st.plotly_chart(fig_hr_ass, use_container_width=True)
                        else:
                            df_h_chart = pd.DataFrame({"Capability": chart_skills, "Score": chart_scores})
                            fig_bar_h = px.bar(df_h_chart, x="Capability", y="Score", range_y=[0, 100], color_discrete_sequence=["#10B981"])
                            fig_bar_h.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10))
                            st.plotly_chart(fig_bar_h, use_container_width=True)
                    else:
                        st.info(f"No assessments recorded for {target_ass_code} yet.")

                if hr_emp_ass:
                    st.markdown("##### Assessment Records Log")
                    hr_ass_records = [
                        {
                            "Skill / Competency": a.get("skill_name") or a.get("name") or "Competency Area",
                            "Score (%)": a.get("score") if a.get("score") is not None else (a.get("assessment_score") or 0),
                            "Manager Notes": a.get("notes") or "",
                            "Evaluation Date": a.get("created_at") or a.get("date") or "",
                        }
                        for a in hr_emp_ass
                    ]
                    df_h_log = pd.DataFrame(hr_ass_records)
                    st.dataframe(df_h_log, width="stretch", hide_index=True)

        with tab_sk_gaps:
            st.markdown("#### Benchmark Role Gap Analysis & Competency Radar")
            st.caption("Compare current verified competencies against 10 corporate benchmark roles to pinpoint development priorities.")
            if emp_sk_map:
                sel_gap_emp = st.selectbox("Select Employee for Gap Analysis", list(emp_sk_map.keys()), key="hr_sel_gap_emp")
                target_gap_code = emp_sk_map[sel_gap_emp]
            else:
                target_gap_code = emp_id

            all_roles = list(ROLE_CATALOG.keys())
            target_role_eval = st.selectbox("Benchmark Target Role", all_roles, key="sel_bench_role")

            gap_result = get_employee_skill_gaps(target_gap_code, target_role_eval, org_id=org_id)
            
            c_radar1, c_radar2 = st.columns([1.1, 1])
            with c_radar1:
                st.metric(f"Match Readiness for {target_role_eval}", f"{gap_result['match_percentage']}%", delta=f"{gap_result['match_percentage']}% Target Alignment")
                st.progress(gap_result['match_percentage'] / 100)

                # Interactive Spider/Radar Chart
                if gap_result["gaps"]:
                    top_gaps = gap_result["gaps"][:6]
                    cat_names = [g["skill"] for g in top_gaps]
                    c_vals = [g["current_level"] for g in top_gaps]
                    r_vals = [g["required_level"] for g in top_gaps]

                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(
                        r=c_vals + [c_vals[0]],
                        theta=cat_names + [cat_names[0]],
                        fill='toself',
                        fillcolor='rgba(37, 99, 235, 0.15)',
                        name='Current Level',
                        line=dict(color='#2563EB', width=2)
                    ))
                    fig_radar.add_trace(go.Scatterpolar(
                        r=r_vals + [r_vals[0]],
                        theta=cat_names + [cat_names[0]],
                        fill='toself',
                        fillcolor='rgba(16, 185, 129, 0.10)',
                        name='Target Benchmark',
                        line=dict(color='#10B981', width=2, dash='dot')
                    ))
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3, 4], ticktext=['Beg', 'Int', 'Adv', 'Exp'])
                        ),
                        showlegend=True,
                        height=290,
                        margin=dict(l=25, r=25, t=25, b=25),
                        paper_bgcolor="#FFFFFF"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)

            with c_radar2:
                st.markdown(f"**Benchmark Role Standard:**")
                st.info(f"{gap_result['criteria']}")
                
                # Interactive Skill Growth Simulator
                st.markdown(f"##### {get_svg_icon('zap', size=16, color='#2563EB')} Interactive Growth Simulator", unsafe_allow_html=True)
                st.caption("Simulate upgrading a competency to see projected role match improvement:")
                if gap_result["gaps"]:
                    sim_skill = st.selectbox("Select Competency to Boost", [g["skill"] for g in gap_result["gaps"]], key="sim_sk_sel")
                    sim_level = st.select_slider("Target Simulated Level", options=[1, 2, 3, 4], value=3, format_func=lambda x: ['None', 'Beginner', 'Intermediate', 'Advanced', 'Expert'][x], key="sim_sk_lvl")
                    old_m = gap_result['match_percentage']
                    boosted_m = min(100, old_m + (sim_level * 5))
                    st.markdown(
                        f"""
                        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 10px 14px; margin-top: 8px;">
                            <span style="font-size: 0.84rem; color: #1E40AF; display: inline-flex; align-items: center; gap: 6px;">
                                Advancing <strong>{sim_skill}</strong> to level {sim_level} projects role readiness from <strong>{old_m}%</strong> {get_svg_icon("arrow_right", size=14, color="#1D4ED8")} <strong style="color: #10B981;">{boosted_m}%</strong> (+{boosted_m - old_m}% gain).
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            if gap_result["gaps"]:
                st.markdown("##### Detailed Priority Competency Breakdown")
                levels_str = {0: "None (0)", 1: "Beginner (1)", 2: "Intermediate (2)", 3: "Advanced (3)", 4: "Expert (4)"}
                render_html(render_colored_gaps_table(gap_result["gaps"], levels_str))

            if gap_result.get("recommended_training"):
                st.markdown("##### Recommended Targeted Training Courses")
                for t_item in gap_result["recommended_training"]:
                    st.markdown(f"• **{t_item}** — Focus program to close competency gaps.")

        with tab_sk_train:
            st.markdown("#### Training & Course Assignments")
            if is_admin:
                with st.form("assign_train_form"):
                    st.markdown("##### Assign Upskilling Course")
                    t_emp = st.selectbox("Assignee Employee", list(emp_sk_map.keys()) if all_emps else [target_code])
                    t_emp_code = emp_sk_map[t_emp] if all_emps else target_code
                    t_course = st.text_input("Course Title *", placeholder="e.g. Enterprise System Design Architecture")
                    t_skill = st.text_input("Target Skill *", placeholder="e.g. System Design")
                    t_provider = st.text_input("Training Provider", value="Talent Growth Academy")
                    t_due = st.date_input("Target Completion Date", value=date.today())
                    submit_train = st.form_submit_button("Assign Course", type="primary")

                if submit_train:
                    ok_tr, msg_tr = add_training_record(t_emp_code, t_course, t_skill, t_provider, t_due.isoformat(), "Enrolled", org_id=org_id)
                    if ok_tr:
                        st.success(msg_tr)
                        st.rerun()
                    else:
                        st.error(msg_tr)

            trainings = get_training_records(org_id=org_id)
            if trainings:
                render_html(render_colored_training_table(trainings))
            else:
                st.info(f"No active training courses recorded for {org_id}.")

# ==============================================================================
# 5B. ROLE MATCH & GAPS
# ==============================================================================
elif page in ["Role Match & Gaps", "Role Match & Competency Gaps", "Competency Gaps"]:
    render_html(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin: 0 0 4px 0;">
                Role match & competency gap analysis
            </h1>
            <div style="font-size: 0.95rem; color: #64748B;">
                Compare your verified competencies against 10 corporate benchmark roles to identify shortfalls and plan development.
            </div>
        </div>
        """
    )

    all_roles = list(ROLE_CATALOG.keys())
    default_role_idx = all_roles.index(profile["target_role"]) if profile.get("target_role") in all_roles else 0
    target_role_eval = st.selectbox("Benchmark Target Role", all_roles, index=default_role_idx, key="sel_role_match_page")

    gap_result = get_employee_skill_gaps(emp_id if emp_id else f"EMP-{uid}", target_role_eval, org_id=org_id)

    c_radar1, c_radar2 = st.columns([1.1, 1], gap="large")
    with c_radar1:
        st.metric(f"Match Readiness for {target_role_eval}", f"{gap_result['match_percentage']}%", delta=f"{gap_result['match_percentage']}% Target Alignment")
        st.progress(gap_result['match_percentage'] / 100)

        if gap_result["gaps"]:
            top_gaps = gap_result["gaps"][:6]
            cat_names = [g["skill"] for g in top_gaps]
            c_vals = [g["current_level"] for g in top_gaps]
            r_vals = [g["required_level"] for g in top_gaps]

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=c_vals + [c_vals[0]],
                theta=cat_names + [cat_names[0]],
                fill='toself',
                fillcolor='rgba(37, 99, 235, 0.15)',
                name='Current Level',
                line=dict(color='#2563EB', width=2)
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=r_vals + [r_vals[0]],
                theta=cat_names + [cat_names[0]],
                fill='toself',
                fillcolor='rgba(16, 185, 129, 0.10)',
                name='Target Benchmark',
                line=dict(color='#10B981', width=2, dash='dot')
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3, 4], ticktext=['Beg', 'Int', 'Adv', 'Exp'])
                ),
                showlegend=True,
                height=290,
                margin=dict(l=25, r=25, t=25, b=25),
                paper_bgcolor="#FFFFFF"
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    with c_radar2:
        st.markdown(f"**Benchmark Role Standard:**")
        st.info(f"{gap_result['criteria']}")
        
        st.markdown(f"##### {get_svg_icon('zap', size=16, color='#2563EB')} Interactive Growth Simulator", unsafe_allow_html=True)
        st.caption("Simulate upgrading a competency to see projected role match improvement:")
        if gap_result["gaps"]:
            sim_skill = st.selectbox("Select Competency to Boost", [g["skill"] for g in gap_result["gaps"]], key="sim_sk_sel_page")
            sim_level = st.select_slider("Target Simulated Level", options=[1, 2, 3, 4], value=3, format_func=lambda x: ['None', 'Beginner', 'Intermediate', 'Advanced', 'Expert'][x], key="sim_sk_lvl_page")
            old_m = gap_result['match_percentage']
            boosted_m = min(100, old_m + (sim_level * 5))
            st.markdown(
                f"""
                <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 10px 14px; margin-top: 8px;">
                    <span style="font-size: 0.84rem; color: #1E40AF; display: inline-flex; align-items: center; gap: 6px;">
                        Advancing <strong>{sim_skill}</strong> to level {sim_level} projects role readiness from <strong>{old_m}%</strong> {get_svg_icon("arrow_right", size=14, color="#1D4ED8")} <strong style="color: #10B981;">{boosted_m}%</strong> (+{boosted_m - old_m}% gain).
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

    if gap_result["gaps"]:
        st.markdown("##### Detailed Priority Competency Breakdown")
        levels_str = {0: "None (0)", 1: "Beginner (1)", 2: "Intermediate (2)", 3: "Advanced (3)", 4: "Expert (4)"}
        render_html(render_colored_gaps_table(gap_result["gaps"], levels_str))

    if gap_result.get("recommended_training"):
        st.markdown("##### Recommended Targeted Training Courses")
        for t_item in gap_result["recommended_training"]:
            st.markdown(f"• **{t_item}** — Focus program to close competency gaps.")

# ==============================================================================
# 6. CAREER DEVELOPMENT & SMART GOALS / GROWTH PROGRESS
# ==============================================================================
elif page in ["Growth Progress", "Career Goals", "Career Development Plans", "My Career Goals"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("goals", size=24, color="#F97316")} Growth Progress & SMART Goals
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Define target designations, track milestone completion, and monitor achievement roadmaps.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">CAREER ROADMAP</span>
            </div>
        </div>
        """
    )


    goal_user_id = None if is_admin else uid
    goal_stats = get_goal_stats(user_id=goal_user_id, org_id=org_id)

    if "cg_status_sel" not in st.session_state:
        st.session_state.cg_status_sel = "All Statuses"

    curr_filter = st.session_state.cg_status_sel

    # INTERACTIVE 5-CARD EXECUTIVE METRIC ROW
    c_m1, c_m2, c_m3, c_m4, c_m5 = st.columns(5, gap="small")

    with c_m1:
        is_act = (curr_filter == "All Statuses")
        act_cls = "active-filter" if is_act else ""
        badge_html = '<span class="pro-metric-badge" style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;">SELECTED</span>' if is_act else '<span class="pro-metric-badge" style="background:#F1F5F9; color:#475569;">100% POOL</span>'
        render_html(f"""
        <div class="pro-metric-card card-blue {act_cls}">
            <div class="pro-metric-header">
                <span class="pro-metric-label">Total Goals</span>
                <div class="pro-metric-icon-wrap">{get_svg_icon("target", size=18, color="#2563EB")}</div>
            </div>
            <div class="pro-metric-value">{goal_stats['total']}</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                <span class="pro-metric-sub">Defined career milestones</span>
                {badge_html}
            </div>
        </div>
        """)
        if st.button("All Goals" if not is_act else "Active ✓", key="btn_card_all", use_container_width=True, type="primary" if is_act else "secondary"):
            st.session_state.cg_status_sel = "All Statuses"
            st.rerun()

    with c_m2:
        is_act = (curr_filter == "In Progress")
        act_cls = "active-filter" if is_act else ""
        badge_html = '<span class="pro-metric-badge" style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A;">SELECTED</span>' if is_act else '<span class="pro-metric-badge" style="background:#FEF3C7; color:#92400E;">25–75%</span>'
        render_html(f"""
        <div class="pro-metric-card card-amber {act_cls}">
            <div class="pro-metric-header">
                <span class="pro-metric-label">In Progress (25–75%)</span>
                <div class="pro-metric-icon-wrap">{get_svg_icon("clock", size=18, color="#D97706")}</div>
            </div>
            <div class="pro-metric-value">{goal_stats['in_progress']}</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                <span class="pro-metric-sub">Active execution</span>
                {badge_html}
            </div>
        </div>
        """)
        if st.button("Filter: In Progress" if not is_act else "Active ✓", key="btn_card_prog", use_container_width=True, type="primary" if is_act else "secondary"):
            st.session_state.cg_status_sel = "In Progress"
            st.rerun()

    with c_m3:
        is_act = (curr_filter == "Completed")
        act_cls = "active-filter" if is_act else ""
        badge_html = '<span class="pro-metric-badge" style="background:#ECFDF5; color:#047857; border:1px solid #A7F3D0;">SELECTED</span>' if is_act else '<span class="pro-metric-badge" style="background:#ECFDF5; color:#065F46;">100% DONE</span>'
        render_html(f"""
        <div class="pro-metric-card card-emerald {act_cls}">
            <div class="pro-metric-header">
                <span class="pro-metric-label">Completed (100%)</span>
                <div class="pro-metric-icon-wrap">{get_svg_icon("check", size=18, color="#059669")}</div>
            </div>
            <div class="pro-metric-value">{goal_stats['completed']}</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                <span class="pro-metric-sub">Finished milestones</span>
                {badge_html}
            </div>
        </div>
        """)
        if st.button("Filter: Done" if not is_act else "Active ✓", key="btn_card_comp", use_container_width=True, type="primary" if is_act else "secondary"):
            st.session_state.cg_status_sel = "Completed"
            st.rerun()

    with c_m4:
        is_act = (curr_filter == "Overdue")
        act_cls = "active-filter" if is_act else ""
        badge_html = '<span class="pro-metric-badge" style="background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA;">SELECTED</span>' if is_act else '<span class="pro-metric-badge" style="background:#FEF2F2; color:#991B1B;">DEADLINE</span>'
        render_html(f"""
        <div class="pro-metric-card card-rose {act_cls}">
            <div class="pro-metric-header">
                <span class="pro-metric-label">Overdue Goals</span>
                <div class="pro-metric-icon-wrap">{get_svg_icon("shield", size=18, color="#DC2626")}</div>
            </div>
            <div class="pro-metric-value">{goal_stats['overdue']}</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                <span class="pro-metric-sub">Past target deadline</span>
                {badge_html}
            </div>
        </div>
        """)
        if st.button("Filter: Overdue" if not is_act else "Active ✓", key="btn_card_overdue", use_container_width=True, type="primary" if is_act else "secondary"):
            st.session_state.cg_status_sel = "Overdue"
            st.rerun()

    with c_m5:
        render_html(f"""
        <div class="pro-metric-card card-purple">
            <div class="pro-metric-header">
                <span class="pro-metric-label">Avg Progress</span>
                <div class="pro-metric-icon-wrap">{get_svg_icon("trending_up", size=18, color="#7C3AED")}</div>
            </div>
            <div class="pro-metric-value">{goal_stats['avg_progress']}%</div>
            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                <span class="pro-metric-sub">Milestone completion</span>
                <span class="pro-metric-badge" style="background:#F5F3FF; color:#6D28D9;">VELOCITY</span>
            </div>
        </div>
        """)
        if st.button("Reset Filter", key="btn_card_reset", use_container_width=True, type="secondary"):
            st.session_state.cg_status_sel = "All Statuses"
            st.rerun()

    # EXECUTIVE OVERALL MILESTONE COMPLETION DASHBOARD BANNER
    avg_pct = goal_stats["avg_progress"]
    total_g = goal_stats["total"]
    comp_g = goal_stats["completed"]
    prog_g = goal_stats["in_progress"]
    over_g = goal_stats["overdue"]
    not_start_g = goal_stats["not_started"]

    if avg_pct >= 75:
        vel_status = "Velocity: Ahead of Target Pace"
        vel_badge_cls = "tbl-badge-green"
        vel_dot_color = "#10B981"
    elif avg_pct >= 40:
        vel_status = "Velocity: Active Flight Momentum"
        vel_badge_cls = "tbl-badge-blue"
        vel_dot_color = "#2563EB"
    elif avg_pct > 0:
        vel_status = "Velocity: Early Acceleration"
        vel_badge_cls = "tbl-badge-yellow"
        vel_dot_color = "#F59E0B"
    else:
        vel_status = "Velocity: Planning & Initiation"
        vel_badge_cls = "tbl-badge-yellow"
        vel_dot_color = "#94A3B8"

    render_html(f"""
    <div class="milestone-exec-banner">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 0.85rem;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 44px; height: 44px; border-radius: 12px; background: #EFF6FF; border: 1px solid #DBEAFE; display: flex; align-items: center; justify-content: center; color: #2563EB; box-shadow: 0 2px 6px rgba(37,99,235,0.12);">
                    {get_svg_icon("goals", size=22, color="#2563EB")}
                </div>
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 1.25rem; font-weight: 800; color: #0F172A; letter-spacing: -0.01em;">Overall Milestone Completion</span>
                        <span style="font-size: 1.35rem; font-weight: 900; color: #2563EB; background: #EFF6FF; border: 1px solid #DBEAFE; padding: 2px 10px; border-radius: 8px;">{avg_pct}%</span>
                    </div>
                    <div style="font-size: 0.84rem; color: #64748B; margin-top: 2px;">
                        <strong>{comp_g} of {total_g}</strong> milestones achieved ({avg_pct}% weighted completion across career roadmap)
                    </div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="tbl-badge {vel_badge_cls}" style="font-size: 0.8rem; padding: 5px 12px;">
                    <span class="tbl-badge-dot" style="background: {vel_dot_color};"></span>
                    {vel_status}
                </span>
            </div>
        </div>

        <div class="milestone-track-container">
            <div class="milestone-track-bar">
                <div class="milestone-track-fill" style="width: {avg_pct}%;"></div>
            </div>
            <div class="milestone-ticks-row">
                <span>0% Defined</span>
                <span>25% Initiated</span>
                <span>50% Mid-Point</span>
                <span>75% Advanced</span>
                <span>100% Achieved</span>
            </div>
        </div>

        <div style="border-top: 1px solid #F1F5F9; margin-top: 1rem; padding-top: 0.85rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                <span class="milestone-chip">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #3B82F6;"></span>
                    In Progress: <strong>{prog_g}</strong>
                </span>
                <span class="milestone-chip">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #10B981;"></span>
                    Completed: <strong>{comp_g}</strong>
                </span>
                <span class="milestone-chip">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #EF4444;"></span>
                    Overdue: <strong>{over_g}</strong>
                </span>
                <span class="milestone-chip">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #94A3B8;"></span>
                    Not Started: <strong>{not_start_g}</strong>
                </span>
            </div>
            <div style="font-size: 0.8rem; color: #64748B;">
                Click any metric card above to dynamically filter milestones below
            </div>
        </div>
    </div>
    """)

    tab_g_view, tab_g_create, tab_g_edit = st.tabs(["Goals Dashboard & Tracking", "Create SMART Career Goal", "Manage Milestones (Edit / Delete)"])

    # --- TAB 1: DASHBOARD ---
    with tab_g_view:
        c_ghead1, c_ghead2 = st.columns([2.2, 1.3])
        with c_ghead1:
            st.markdown("#### Active Career Goals & Milestone Roadmap")
            st.caption("SMART goals aligned with career objectives, target milestones, and completion schedules.")
        with c_ghead2:
            goal_view_mode = st.radio("Goal View Layout", ["Roadmap View", "Table View"], horizontal=True, key="goal_view_mode", label_visibility="collapsed")

        status_options = ["All Statuses", "In Progress", "Completed", "Overdue", "Not Started"]
        if st.session_state.cg_status_sel not in status_options:
            st.session_state.cg_status_sel = "All Statuses"

        c_flt1, c_flt2 = st.columns([3, 1])
        with c_flt1:
            status_filter = st.selectbox(
                "Filter Goals by Status",
                status_options,
                index=status_options.index(st.session_state.cg_status_sel),
                key="cg_status_sel_box"
            )
            if status_filter != st.session_state.cg_status_sel:
                st.session_state.cg_status_sel = status_filter
                st.rerun()

        with c_flt2:
            st.write("")
            st.write("")
            if status_filter != "All Statuses":
                if st.button("Clear Filter", key="btn_inline_reset_filter", use_container_width=True):
                    st.session_state.cg_status_sel = "All Statuses"
                    st.rerun()

        goals_data = get_goals(user_id=goal_user_id, status_filter=status_filter if status_filter != "All Statuses" else None, org_id=org_id)

        if goals_data:
            if goal_view_mode == "Roadmap View":
                for g in goals_data:
                    status_bar_cls = "goal-bar-completed" if g["status"] == "Completed" else ("goal-bar-overdue" if g["status"] == "Overdue" else "goal-bar-progress")
                    badge_cls = "badge-completed" if g["status"] == "Completed" else ("badge-overdue" if g["status"] == "Overdue" else "badge-progress")
                    
                    render_html(
                        f"""
                        <div class="goal-interactive-card">
                            <div class="{status_bar_cls}"></div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                                <div>
                                    <span style="font-weight: 800; font-size: 1.1rem; color: #0F172A;">{g['title']}</span>
                                    <span style="font-size: 0.8rem; color: #2563EB; margin-left: 8px; font-weight: 600;">{g['target_designation'] or 'General Growth'}</span>
                                </div>
                                <span class="badge-status {badge_cls}">{g['status'].upper()}</span>
                            </div>
                            <div style="font-size: 0.86rem; color: #475569; margin-bottom: 12px;">
                                {g['description'] or 'Delivering measurable impact toward professional promotion benchmarks.'}
                            </div>
                            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; color: #64748B; margin-bottom: 4px;">
                                <span>Target Completion: <strong>{g['target_date']}</strong></span>
                                <span style="font-weight: 800; color: #0F172A;">{g['progress']}% Complete</span>
                            </div>
                        </div>
                        """
                    )
                    st.progress(g["progress"] / 100)
                    
                    # Interactive milestone advance buttons
                    col_act1, col_act2, col_act3 = st.columns([2.5, 1, 1])
                    with col_act2:
                        if g["progress"] < 100:
                            new_val = min(100, g["progress"] + 25)
                            if st.button(f"Advance +25%", key=f"adv_btn_{g['id']}", use_container_width=True):
                                update_goal_progress(g["id"], uid, new_val)
                                st.rerun()
                    with col_act3:
                        if g["progress"] < 100:
                            if st.button("Mark as Completed", key=f"comp_btn_{g['id']}", type="primary", use_container_width=True):
                                update_goal_progress(g["id"], uid, 100)
                                st.rerun()
                    st.markdown("<div style='margin-bottom: 14px;'></div>", unsafe_allow_html=True)
            else:
                render_html(render_colored_goals_table(goals_data))

            fig_goals = px.bar(
                pd.DataFrame(goals_data),
                x="title", y="progress", color="status",
                range_y=[0, 100],
                title="Goal Progress & Milestone Completion (%)",
                labels={"title": "Career Goal", "progress": "Progress (%)", "status": "Status"},
                color_discrete_map={"Not Started": "#94A3B8", "In Progress": "#3B82F6", "Completed": "#10B981", "Overdue": "#EF4444"},
                height=260
            )
            fig_goals.update_layout(margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_goals, use_container_width=True)

            # Quick Milestone Updater
            st.divider()
            st.markdown("##### Quick Progress Milestone Updater")
            q1, q2, q3 = st.columns([2, 1, 1])
            with q1:
                q_map = {f"{g['title']} (Current: {g['progress']}%)": g["id"] for g in goals_data}
                sel_q_goal = st.selectbox("Select Goal to Update", list(q_map.keys()))
                q_gid = q_map[sel_q_goal]
            with q2:
                curr_g_obj = next(g for g in goals_data if g["id"] == q_gid)
                new_prog_val = st.selectbox(
                    "New Milestone", [0, 25, 50, 75, 100],
                    index=[0, 25, 50, 75, 100].index(curr_g_obj["progress"])
                )
            with q3:
                st.write("")
                st.write("")
                if st.button("Update Milestone", type="primary", use_container_width=True):
                    ok_qp, msg_qp = update_goal_progress(q_gid, uid, new_prog_val)
                    if ok_qp:
                        st.success(msg_qp)
                        st.rerun()
                    else:
                        st.error(msg_qp)
        else:
            render_html(f"""
            <div style="background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 14px; padding: 2.25rem 1.5rem; text-align: center; margin: 1.25rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="width: 48px; height: 48px; border-radius: 12px; background: #EFF6FF; color: #2563EB; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                    {get_svg_icon("goals", size=24, color="#2563EB")}
                </div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 4px;">No Goals with Status '{status_filter}'</div>
                <div style="font-size: 0.88rem; color: #64748B; max-width: 460px; margin: 0 auto 1.25rem auto;">
                    There are currently no career milestones matching this status filter. You can reset filters to view all active objectives.
                </div>
            </div>
            """)
            c_e1, c_e2, c_e3 = st.columns([1.5, 1, 1.5])
            with c_e2:
                if st.button("Show All Career Goals", key="btn_empty_show_all", use_container_width=True, type="primary"):
                    st.session_state.cg_status_sel = "All Statuses"
                    st.rerun()

    # --- TAB 2: CREATE GOAL ---
    with tab_g_create:
        st.markdown("#### Create SMART Career Goal")
        st.caption("Define target role, action steps, completion deadline, and discrete progress milestone.")

        with st.form("create_career_goal_form"):
            cg_title = st.text_input("Goal Title *", placeholder="e.g. Master Enterprise System Design & Distributed Systems")
            cg_role = st.selectbox("Target Designation", ["Not Specified"] + list(ROLE_CATALOG.keys()))
            cg_desc = st.text_area("Action Steps & Deliverables", placeholder="Specific certifications, projects, or milestones to achieve...")
            cg_date = st.date_input("Target Completion Date *", min_value=date.today())
            cg_prog = st.select_slider(
                "Initial Progress Milestone", options=[0, 25, 50, 75, 100], value=0,
                format_func=lambda x: f"{x}% ({'Not Started' if x==0 else ('Completed' if x==100 else 'In Progress')})"
            )

            submit_cg = st.form_submit_button("Save Career Goal to Database", type="primary", use_container_width=True)

        if submit_cg:
            if not cg_title.strip():
                st.error("Validation Error: Goal Title is required.")
            elif not cg_date:
                st.error("Validation Error: Target Date is required.")
            else:
                ok_cg, msg_cg = add_goal(
                    user_id=uid,
                    title=cg_title,
                    description=cg_desc,
                    target_date=cg_date.isoformat(),
                    progress=cg_prog,
                    employee_id=emp_id,
                    target_designation="" if cg_role == "Not Specified" else cg_role,
                    org_id=org_id
                )
                if ok_cg:
                    st.success(msg_cg)
                    st.rerun()
                else:
                    st.error(msg_cg)

    # --- TAB 3: MANAGE GOALS ---
    with tab_g_edit:
        st.markdown("#### Edit or Delete Career Goals")
        my_all_goals = get_goals(user_id=goal_user_id, org_id=org_id)
        if not my_all_goals:
            st.info("No goals available to manage.")
        else:
            g_edit_map = {f"{g['title']} (Due: {g['target_date']})": g["id"] for g in my_all_goals}
            sel_g_label = st.selectbox("Select Goal to Modify", list(g_edit_map.keys()))
            sel_gid = g_edit_map[sel_g_label]
            target_g_obj = get_goal_by_id(sel_gid)

            if target_g_obj:
                c_ged, c_gdel = st.columns([1.6, 1])
                with c_ged:
                    with st.form("edit_career_goal_form"):
                        st.markdown(f"##### Edit Details for *{target_g_obj['title']}*")
                        ed_title = st.text_input("Goal Title", value=target_g_obj["title"])
                        role_keys = ["Not Specified"] + list(ROLE_CATALOG.keys())
                        curr_rk_idx = role_keys.index(target_g_obj.get("target_designation")) if target_g_obj.get("target_designation") in role_keys else 0
                        ed_role = st.selectbox("Target Designation", role_keys, index=curr_rk_idx)
                        ed_desc = st.text_area("Action Steps", value=target_g_obj["description"])
                        try:
                            def_d = datetime.strptime(target_g_obj["target_date"], "%Y-%m-%d").date()
                        except Exception:
                            def_d = date.today()
                        ed_date = st.date_input("Target Date", value=def_d)
                        ed_prog = st.select_slider(
                            "Milestone Progress",
                            options=[0, 25, 50, 75, 100],
                            value=target_g_obj["progress"],
                            format_func=lambda x: f"{x}% ({'Not Started' if x==0 else ('Completed' if x==100 else 'In Progress')})"
                        )
                        update_g_btn = st.form_submit_button("Update Goal", type="primary")

                    if update_g_btn:
                        ok_gu, msg_gu = update_goal(
                            goal_id=sel_gid,
                            user_id=uid,
                            title=ed_title,
                            description=ed_desc,
                            target_date=ed_date.isoformat(),
                            progress=ed_prog,
                            target_designation="" if ed_role == "Not Specified" else ed_role
                        )
                        if ok_gu:
                            st.success(msg_gu)
                            st.rerun()
                        else:
                            st.error(msg_gu)

                with c_gdel:
                    with st.container(border=True):
                        st.markdown("##### Remove Career Goal")
                        st.write(f"Are you sure you want to delete **{target_g_obj['title']}**?")
                        st.caption("Permanent action. Associated progress logs will be purged.")
                        confirm_g_del = st.checkbox("I confirm deletion of this career goal.")
                        if st.button("Delete Goal", type="secondary", disabled=not confirm_g_del):
                            ok_gdel, msg_gdel = delete_goal(sel_gid, uid)
                            if ok_gdel:
                                st.success(msg_gdel)
                                st.rerun()
                            else:
                                st.error(msg_gdel)

# ==============================================================================
# 7. REPORTS & ANALYTICS
# ==============================================================================
elif page in ["Career Report", "Reports", "Reports & Analytics", "Career Growth Report"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("reports", size=24, color="#2563EB")} Executive Reports & Data Center
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Generate publication-grade PDF talent dossiers, structured CSV data exports, and organizational benchmarks.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">REPORTING ENGINE</span>
            </div>
        </div>
        """
    )

    employees = get_employees(org_id=org_id)
    reviews = get_performance_reviews(org_id=org_id)
    goals = get_goals(org_id=org_id)
    dept_summary = get_department_performance_summary(org_id=org_id)
    tab_rep_overview, tab_rep_csv, tab_rep_pdf = st.tabs(["Analytics Overview", "Download CSV Data Reports", "Generate PDF Dossier"])

    with tab_rep_overview:
        render_html(
            f"""
            <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 0.5rem 0 0.85rem 0;">
                {get_svg_icon("briefcase", size=20, color="#2563EB")} Department Workforce & Performance Breakdown
            </div>
            """
        )
        if dept_summary:
            render_html(render_colored_dept_summary_table(dept_summary))

        if employees:
            df_status = pd.DataFrame(employees)["employment_status"].value_counts().reset_index()
            df_status.columns = ["Status", "Count"]
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                fig_st = px.pie(
                    df_status, values="Count", names="Status", title="Employment Status Distribution",
                    hole=0.35, color_discrete_sequence=['#10B981', '#F59E0B', '#64748B']
                )
                fig_st.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=300)
                st.plotly_chart(fig_st, use_container_width=True)
            with c_p2:
                if reviews:
                    fig_scat = px.scatter(
                        pd.DataFrame(reviews), x="performance_score", y="department", color="review_period",
                        title="Performance Ratings across Departments",
                        labels={"performance_score": "Rating (1-5)", "department": "Department"},
                        color_discrete_sequence=['#2563EB', '#10B981', '#F59E0B']
                    )
                    fig_scat.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=300)
                    st.plotly_chart(fig_scat, use_container_width=True)

    with tab_rep_csv:
        st.markdown("#### Download Structured CSV Data Reports")
        c_csv1, c_csv2 = st.columns(2)
        with c_csv1:
            if employees:
                csv_emp = pd.DataFrame(employees).to_csv(index=False).encode("utf-8")
                st.download_button("Download Employees (CSV)", csv_emp, "talent_growth_employees.csv", "text/csv", type="primary", use_container_width=True)
            if reviews:
                st.write("")
                csv_rev = pd.DataFrame(reviews).to_csv(index=False).encode("utf-8")
                st.download_button("Download Performance Reviews (CSV)", csv_rev, "talent_growth_performance_reviews.csv", "text/csv", use_container_width=True)
        with c_csv2:
            if goals:
                csv_goal = pd.DataFrame(goals).to_csv(index=False).encode("utf-8")
                st.download_button("Download Career Goals (CSV)", csv_goal, "talent_growth_career_goals.csv", "text/csv", use_container_width=True)
            st.write("")
            payload_json = json.dumps(export_user_data(uid), indent=2, default=str).encode("utf-8")
            st.download_button("Export System Snapshot (JSON)", payload_json, "talent_growth_snapshot.json", "application/json", use_container_width=True)

    with tab_rep_pdf:
        st.markdown("#### Generate Publication-Grade PDF Talent Dossier")
        st.caption("Creates an executive multi-page dossier incorporating verified skills, gap metrics, goal milestones, and performance reviews.")
        a = analysis_bundle()
        gaps = gap_analysis(profile.get("target_role", ""), skills)
        recs = recommendations(profile, skills)
        assessments = get_assessments(uid=uid, employee_id=emp_id, org_id=org_id)
        progress = get_progress(uid)
        user_goals = get_goals(user_id=uid, org_id=org_id)
        user_reviews = get_performance_reviews(employee_id=emp_id, org_id=org_id)

        pdf_bytes = create_report(
            profile=profile,
            skills=skills,
            analysis=a,
            gaps=gaps,
            recommendations=recs,
            assessments=assessments,
            progress=progress,
            goals=user_goals,
            reviews=user_reviews
        )

        st.download_button(
            "Download PDF Talent Dossier",
            pdf_bytes,
            file_name=f"talent_growth_dossier_{emp_id}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

# ==============================================================================
# 8. MY PROFILE
# ==============================================================================
elif page == "My Profile":
    st.markdown("<h1 style='font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin-bottom: 0.85rem;'>My professional profile</h1>", unsafe_allow_html=True)

    org_display_name = user.get("org_name") or profile.get("company") or "Talent Growth Technologies"
    org_display_id = user.get("org_id", "ORG-TALENT-01")
    render_html(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px 18px; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 38px; height: 38px; border-radius: 10px; background: #EFF6FF; color: #2563EB; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 3px rgba(37, 99, 235, 0.1);">
                    {get_svg_icon("building", size=20, color="#2563EB")}
                </div>
                <div>
                    <div style="font-size: 0.72rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em;">Organization Membership</div>
                    <div style="font-size: 1.05rem; font-weight: 800; color: #0F172A;">{org_display_name}</div>
                </div>
            </div>
            <div style="font-size: 0.8rem; font-family: monospace; font-weight: 700; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 4px 10px; border-radius: 6px;">
                {org_display_id}
            </div>
        </div>
        """
    )

    with st.form("my_profile_form"):
        col_p1, col_p2 = st.columns(2, gap="large")
        with col_p1:
            st.text_input("Full name", value=user.get("name", ""), disabled=True)
            phone = st.text_input("Phone", value=profile.get("phone", ""))
            location = st.text_input("Location", value=profile.get("location", ""))
            job = st.text_input("Current job title", value=profile.get("job_title", ""))
            company = st.text_input("Company", value=profile.get("company", org_display_name))
            department = st.text_input("Department", value=profile.get("department", ""))
            industry = st.text_input("Industry", value=profile.get("industry", ""))
        with col_p2:
            emp_types = ["Full-time", "Part-time", "Contract", "Internship", "Freelance", "Other"]
            curr_emp = profile.get("employment_type")
            emp_idx = emp_types.index(curr_emp) if curr_emp in emp_types else 0
            employment = st.selectbox("Employment type", emp_types, index=emp_idx)
            years = st.number_input("Years of experience", min_value=0.0, max_value=60.0, value=float(profile.get("years_experience") or 0.0), step=0.5, format="%.2f")
            linkedin = st.text_input("LinkedIn URL", value=profile.get("linkedin", ""))
            github = st.text_input("GitHub URL", value=profile.get("github", ""))
            portfolio = st.text_input("Portfolio URL", value=profile.get("portfolio", ""))
            education = st.text_area("Education", value=profile.get("education", ""), placeholder="Degree - Institution - Year", height=68)
            certifications = st.text_area("Certifications", value=profile.get("certifications", ""), height=68)

        summary = st.text_area("Professional summary", value=profile.get("summary", ""), height=80)
        experience = st.text_area("Experience", value=profile.get("experience", ""), placeholder="Role, company, dates, responsibilities, measurable outcomes", height=90)
        projects = st.text_area("Projects and achievements", value=profile.get("projects", ""), height=80)

        submitted_prof = st.form_submit_button("Save profile", type="primary")

        if submitted_prof:
            save_profile(uid, {
                "phone": phone, "location": location, "job_title": job, "company": company,
                "department": department, "industry": industry, "employment_type": employment,
                "years_experience": years, "linkedin": linkedin, "github": github,
                "portfolio": portfolio, "education": education, "certifications": certifications,
                "summary": summary, "experience": experience, "projects": projects
            })
            st.success("Profile saved successfully!")
            st.rerun()

    completion, missing = profile_completion(profile, skills)
    st.markdown(f"<div style='font-size: 0.88rem; font-weight: 600; color: #475569; margin-top: 1rem;'>Profile completion {completion}%</div>", unsafe_allow_html=True)
    st.progress(completion / 100)

    standard_missing_msg = "Phone and location, Current role and employer, Professional summary, Education, Skills, Experience, Certifications, Projects, Career goal and target role, Professional link, Resume content"
    active_missing_msg = ", ".join(missing) if missing else "All essential sections complete!"
    st.caption(f"Still to add: {active_missing_msg if missing else standard_missing_msg}")


elif page == "ATS Resume Studio" or page == "Resume Studio":
    st.markdown("<h1 style='font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin-bottom: 0.35rem;'>Resume Studio</h1>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.95rem; color: #64748B; margin-bottom: 1.25rem;'>Create, edit, and optimize your ATS-ready resume with real-time screening, STAR bullet rewrites, and PDF export.</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # HR ADMINISTRATOR vs EMPLOYEE MODE
    # --------------------------------------------------------------------------
    active_target_uid = uid
    active_target_user = user
    active_target_profile = profile

    if is_admin:
        org_employees = get_employees(org_id=org_id)
        render_html(
            f"""
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 12px 16px; margin-bottom: 1.2rem; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <strong style="color: #1E40AF; font-size: 0.95rem;">HR Administration Mode &bull; Candidate Resume Review</strong>
                    <div style="color: #3B82F6; font-size: 0.83rem;">Select an employee in {org_name} to inspect their resume, review ATS alignment, or download their dossier.</div>
                </div>
                <span class="badge-status badge-active" style="background: #DBEAFE; color: #1E40AF; border-color: #93C5FD;">HR ACCESS</span>
            </div>
            """
        )
        if not org_employees:
            st.info("No employee accounts registered under your organization yet.")
            st.stop()

        emp_options = {f"{e['name']} ({e['employee_id']} - {e.get('designation', 'Staff')})": e for e in org_employees}
        selected_emp_label = st.selectbox("Select Employee Candidate", list(emp_options.keys()), key="hr_resume_emp_selector")
        selected_emp = emp_options[selected_emp_label]
        
        # Resolve target user id
        target_uid_resolved = selected_emp.get("user_id")
        if not target_uid_resolved:
            # Query user ID by employee_id or email
            u_cand = get_user_by_id(selected_emp.get("id"))
            target_uid_resolved = u_cand.get("id") if u_cand else uid

        active_target_uid = target_uid_resolved
        active_target_user = {
            "id": active_target_uid,
            "name": selected_emp["name"],
            "email": selected_emp.get("email", ""),
            "employee_id": selected_emp["employee_id"],
            "org_id": org_id,
            "org_name": org_name
        }
        active_target_profile = get_profile(active_target_uid)

    # --------------------------------------------------------------------------
    # RESUME DATA STATE MANAGEMENT
    # --------------------------------------------------------------------------
    res_session_key = f"resume_data_{active_target_uid}"
    if res_session_key not in st.session_state:
        db_resume = get_resume(active_target_uid, org_id=org_id)
        st.session_state[res_session_key] = db_resume if db_resume else {}

    res_data = st.session_state[res_session_key]

    # Metrics Summary Row
    summary_txt = res_data.get("summary", "")
    skills_list = res_data.get("skills", [])
    exp_list = res_data.get("experience", [])
    edu_list = res_data.get("education", [])
    certs_list = res_data.get("certifications", [])
    projs_list = res_data.get("projects", [])
    links_list = res_data.get("links", [])

    render_html(
        f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; margin-bottom: 1.4rem;">
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 14px; border-radius: 10px;">
                <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Professional Summary</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: {'#10B981' if summary_txt else '#F59E0B'};">{'Ready' if summary_txt else 'Pending'}</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 14px; border-radius: 10px;">
                <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Core Skills</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #2563EB;">{len(skills_list)} Skills</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 14px; border-radius: 10px;">
                <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Work Experience</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A;">{len(exp_list)} Roles</div>
            </div>
            <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px 14px; border-radius: 10px;">
                <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Projects &amp; Certs</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #7C3AED;">{len(projs_list) + len(certs_list)} Items</div>
            </div>
        </div>
        """
    )

    # --------------------------------------------------------------------------
    # TAB SELECTION: Editor, Live Preview & Export, AI ATS Screener
    # --------------------------------------------------------------------------
    if is_admin:
        tab_preview, tab_screener = st.tabs(["ATS Resume Preview & PDF", "AI ATS Screener & Candidate Audit"])
        tab_editor = None
    else:
        tab_editor, tab_preview, tab_screener = st.tabs(["Interactive Resume Editor", "ATS Resume Preview & PDF", "AI ATS Screener & Bullet Optimizer"])

    # ==========================================================================
    # TAB 1: INTERACTIVE RESUME EDITOR (EMPLOYEE ONLY)
    # ==========================================================================
    if tab_editor is not None:
        with tab_editor:
            st.markdown("<h3 style='font-size: 1.25rem; font-weight: 800; color: #0F172A; margin: 0.5rem 0 1rem 0;'>Edit Your Resume Sections</h3>", unsafe_allow_html=True)
            
            # --- SECTION A: PROFESSIONAL SUMMARY ---
            with st.expander("Section A &bull; Professional Summary", expanded=True):
                st.caption("Write a 2-4 sentence executive summary highlighting your domain focus, key technologies, and career trajectory.")
                current_sum = res_data.get("summary", "")
                new_summary = st.text_area(
                    "Professional Summary",
                    value=current_sum,
                    height=100,
                    key=f"rs_summary_area_{active_target_uid}",
                    placeholder="Full stack engineer passionate about scalable cloud systems, microservices, and React frontends."
                )
                res_data["summary"] = new_summary

                col_sum_act1, col_sum_act2, _ = st.columns([2, 2, 4])
                with col_sum_act1:
                    if st.button("Use Recommended Template", key="btn_rs_sum_template"):
                        res_data["summary"] = "Full stack engineer passionate about scalable cloud systems, microservices, and React frontends."
                        st.session_state[res_session_key] = res_data
                        st.rerun()
                with col_sum_act2:
                    if st.button("Clear Summary", key="btn_rs_sum_clear"):
                        res_data["summary"] = ""
                        st.session_state[res_session_key] = res_data
                        st.rerun()

            # --- SECTION B: SKILLS & COMPETENCIES ---
            with st.expander(f"Section B &bull; Core Competencies & Skills ({len(skills_list)} added)", expanded=True):
                st.caption("Add technical proficiencies and domain skills. You can also import verified skills from your Skills & Assessment module.")
                
                # Render existing skills as tags
                if skills_list:
                    st.write("**Current Skills:**")
                    cols_skills = st.columns(min(4, max(1, len(skills_list))))
                    for idx, s in enumerate(skills_list):
                        col_idx = idx % len(cols_skills)
                        with cols_skills[col_idx]:
                            s_name = s.get("name", "")
                            s_prof = s.get("proficiency", "Intermediate")
                            c_tag, c_del = st.columns([3, 1])
                            with c_tag:
                                st.markdown(
                                    f"""
                                    <div style="background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 8px; font-size: 0.82rem; font-weight: 700; color: #1E293B;">
                                        {s_name} <span style="font-size: 0.72rem; color: #2563EB; font-weight: 600;">({s_prof})</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                            with c_del:
                                if st.button("✕", key=f"btn_rs_del_skill_{idx}_{active_target_uid}", help=f"Remove {s_name}"):
                                    res_data["skills"].pop(idx)
                                    st.session_state[res_session_key] = res_data
                                    st.rerun()

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                col_add_sname, col_add_sprof, col_add_sbtn = st.columns([3, 2, 2])
                with col_add_sname:
                    new_skill_name = st.text_input("Skill Name", key="rs_new_skill_input", placeholder="e.g. Python, SQL, React")
                with col_add_sprof:
                    new_skill_prof = st.selectbox("Proficiency", list(LEVELS.keys()), index=1, key="rs_new_skill_prof")
                with col_add_sbtn:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("+ Add Skill", key="btn_rs_add_skill", type="secondary", use_container_width=True):
                        if new_skill_name.strip():
                            existing_names = [s["name"].lower() for s in res_data.get("skills", [])]
                            if new_skill_name.strip().lower() in existing_names:
                                st.warning(f"Skill '{new_skill_name.strip()}' is already in your resume.")
                            else:
                                if "skills" not in res_data:
                                    res_data["skills"] = []
                                res_data["skills"].append({"name": new_skill_name.strip(), "proficiency": new_skill_prof})
                                st.session_state[res_session_key] = res_data
                                st.success(f"Added '{new_skill_name.strip()}'")
                                st.rerun()
                        else:
                            st.warning("Please enter a skill name.")

                # Integration with Skills & Assessment
                st.markdown("<div style='margin-top: 0.75rem; border-top: 1px dashed #E2E8F0; padding-top: 0.75rem;'></div>", unsafe_allow_html=True)
                col_imp_btn, col_imp_info = st.columns([2.5, 5.5])
                with col_imp_btn:
                    if st.button("+ Import from Skills & Assessment", key="btn_rs_import_skills", type="secondary", use_container_width=True):
                        updated_skills = import_skills_to_resume(active_target_uid, res_data.get("skills", []), org_id=org_id)
                        added_count = len(updated_skills) - len(res_data.get("skills", []))
                        res_data["skills"] = updated_skills
                        st.session_state[res_session_key] = res_data
                        st.success(f"Successfully synchronized {added_count} new skills from your Skills & Assessment profile!")
                        st.rerun()
                with col_imp_info:
                    st.caption("Imports your verified employee competencies without overwriting existing manually created resume entries.")

            # --- SECTION C: WORK EXPERIENCE ---
            with st.expander(f"Section C &bull; Work Experience ({len(exp_list)} entries)", expanded=True):
                st.caption("Chronological employment history with measurable outcomes, responsibilities, and leadership impact.")

                if exp_list:
                    for idx, e in enumerate(exp_list):
                        with st.container(border=True):
                            col_exp_head, col_exp_ctrl = st.columns([5, 2])
                            with col_exp_head:
                                date_badge = f"{e.get('start_date', '')} – {e.get('end_date', 'Present')}"
                                st.markdown(
                                    f"""
                                    <div style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">{e.get('job_title', 'Role')} &mdash; <span style="color: #2563EB;">{e.get('company', 'Company')}</span></div>
                                    <div style="font-size: 0.83rem; color: #64748B;">{e.get('location', '')} &bull; {e.get('employment_type', 'Full-time')} &bull; <strong>{date_badge}</strong></div>
                                    """,
                                    unsafe_allow_html=True
                                )
                            with col_exp_ctrl:
                                c_up, c_down, c_del = st.columns(3)
                                with c_up:
                                    if idx > 0 and st.button("↑", key=f"btn_exp_up_{idx}", help="Move Up"):
                                        exp_list[idx - 1], exp_list[idx] = exp_list[idx], exp_list[idx - 1]
                                        res_data["experience"] = exp_list
                                        st.session_state[res_session_key] = res_data
                                        st.rerun()
                                with c_down:
                                    if idx < len(exp_list) - 1 and st.button("↓", key=f"btn_exp_down_{idx}", help="Move Down"):
                                        exp_list[idx + 1], exp_list[idx] = exp_list[idx], exp_list[idx + 1]
                                        res_data["experience"] = exp_list
                                        st.session_state[res_session_key] = res_data
                                        st.rerun()
                                with c_del:
                                    if st.button("✕", key=f"btn_exp_del_{idx}", help="Delete Entry"):
                                        exp_list.pop(idx)
                                        res_data["experience"] = exp_list
                                        st.session_state[res_session_key] = res_data
                                        st.rerun()

                            desc_val = e.get("description", "")
                            if desc_val:
                                st.markdown(f"<div style='font-size: 0.88rem; color: #334155; margin-top: 6px; line-height: 1.5;'>{desc_val}</div>", unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                with st.expander("+ Add Work Experience Entry", expanded=False):
                    with st.form("form_add_experience"):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            new_e_title = st.text_input("Job Title*", placeholder="Senior Software Engineer")
                            new_e_comp = st.text_input("Company Name*", placeholder="Tech Innovations Inc.")
                            new_e_type = st.selectbox("Employment Type", ["Full-time", "Part-time", "Contract", "Internship", "Freelance"])
                        with col_e2:
                            new_e_loc = st.text_input("Location", placeholder="Bangalore, India or Remote")
                            new_e_start = st.text_input("Start Date* (YYYY-MM or YYYY)", placeholder="2023-01")
                            new_e_curr = st.checkbox("Currently working in this role", value=True)
                            new_e_end = st.text_input("End Date (YYYY-MM or YYYY)", placeholder="2024-06", disabled=new_e_curr)

                        new_e_desc = st.text_area("Job Description & Measurable Achievements", placeholder="Architected scalable microservices, reduced latency by 35%, and led a team of 4 engineers.", height=90)
                        btn_submit_exp = st.form_submit_button("+ Add Experience Record", type="primary")

                        if btn_submit_exp:
                            if not new_e_title.strip() or not new_e_comp.strip() or not new_e_start.strip():
                                st.error("Job title, company name, and start date are required.")
                            else:
                                end_val = "Present" if new_e_curr else new_e_end.strip()
                                ok_dt, err_dt = validate_date_range(new_e_start.strip(), end_val, new_e_curr)
                                if not ok_dt:
                                    st.error(err_dt)
                                else:
                                    if "experience" not in res_data:
                                        res_data["experience"] = []
                                    res_data["experience"].append({
                                        "id": f"exp_{len(res_data['experience']) + 1}",
                                        "job_title": new_e_title.strip(),
                                        "company": new_e_comp.strip(),
                                        "employment_type": new_e_type,
                                        "location": new_e_loc.strip(),
                                        "start_date": new_e_start.strip(),
                                        "end_date": end_val,
                                        "is_current": new_e_curr,
                                        "description": new_e_desc.strip()
                                    })
                                    st.session_state[res_session_key] = res_data
                                    st.success(f"Added '{new_e_title.strip()}' at '{new_e_comp.strip()}'")
                                    st.rerun()

            # --- SECTION D: EDUCATION ---
            with st.expander(f"Section D &bull; Education ({len(edu_list)} entries)", expanded=True):
                st.caption("Academic degrees, university education, fields of study, and honors.")
                
                if edu_list:
                    for idx, ed in enumerate(edu_list):
                        with st.container(border=True):
                            col_edu_head, col_edu_ctrl = st.columns([5, 1])
                            with col_edu_head:
                                date_str = f"{ed.get('start_date', '')} – {ed.get('end_date', '')}"
                                st.markdown(
                                    f"""
                                    <div style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">{ed.get('degree', 'Degree')} &mdash; <span style="color: #2563EB;">{ed.get('institution', 'Institution')}</span></div>
                                    <div style="font-size: 0.83rem; color: #64748B;">{ed.get('field_of_study', '')} &bull; <strong>{date_str}</strong></div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                if ed.get("details"):
                                    st.markdown(f"<div style='font-size: 0.86rem; color: #334155; margin-top: 4px;'>{ed['details']}</div>", unsafe_allow_html=True)
                            with col_edu_ctrl:
                                if st.button("✕", key=f"btn_edu_del_{idx}", help="Delete Entry"):
                                    edu_list.pop(idx)
                                    res_data["education"] = edu_list
                                    st.session_state[res_session_key] = res_data
                                    st.rerun()

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                with st.expander("+ Add Education Entry", expanded=False):
                    with st.form("form_add_education"):
                        col_ed1, col_ed2 = st.columns(2)
                        with col_ed1:
                            new_ed_degree = st.text_input("Degree / Qualification*", placeholder="B.Tech in Computer Science")
                            new_ed_inst = st.text_input("Institution / University*", placeholder="National Institute of Technology")
                            new_ed_field = st.text_input("Field of Study", placeholder="Computer Science & Engineering")
                        with col_ed2:
                            new_ed_start = st.text_input("Start Year / Date", placeholder="2019")
                            new_ed_end = st.text_input("End Year / Graduation Date", placeholder="2023")
                            new_ed_details = st.text_area("Relevant Details (GPA, Honors)", placeholder="Graduated with First Class Honors, GPA 8.9/10", height=68)

                        btn_submit_edu = st.form_submit_button("+ Add Education Record", type="primary")
                        if btn_submit_edu:
                            if not new_ed_degree.strip() or not new_ed_inst.strip():
                                st.error("Degree and Institution are required.")
                            else:
                                ok_edt, err_edt = validate_date_range(new_ed_start.strip(), new_ed_end.strip())
                                if not ok_edt:
                                    st.error(err_edt)
                                else:
                                    if "education" not in res_data:
                                        res_data["education"] = []
                                    res_data["education"].append({
                                        "id": f"edu_{len(res_data['education']) + 1}",
                                        "degree": new_ed_degree.strip(),
                                        "institution": new_ed_inst.strip(),
                                        "field_of_study": new_ed_field.strip(),
                                        "start_date": new_ed_start.strip(),
                                        "end_date": new_ed_end.strip(),
                                        "details": new_ed_details.strip()
                                    })
                                    st.session_state[res_session_key] = res_data
                                    st.success(f"Added '{new_ed_degree.strip()}'")
                                    st.rerun()

            # --- SECTION E: CERTIFICATIONS ---
            with st.expander(f"Section E &bull; Certifications & Credentials ({len(certs_list)} entries)", expanded=True):
                st.caption("Professional licenses, vendor credentials, and technical accreditations.")

                if certs_list:
                    for idx, c in enumerate(certs_list):
                        with st.container(border=True):
                            col_c_head, col_c_ctrl = st.columns([5, 1])
                            with col_c_head:
                                st.markdown(
                                    f"""
                                    <div style="font-weight: 800; font-size: 1.0rem; color: #0F172A;">{c.get('name', 'Certification')} &mdash; <span style="color: #2563EB;">{c.get('issuing_org', '')}</span></div>
                                    <div style="font-size: 0.83rem; color: #64748B;">Issued: {c.get('issue_date', 'N/A')} &bull; ID: {c.get('credential_id', 'N/A')}</div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                if c.get("credential_url"):
                                    st.markdown(f"<a href='{c['credential_url']}' target='_blank' style='font-size: 0.82rem; color: #2563EB;'>Verify Credential</a>", unsafe_allow_html=True)
                            with col_c_ctrl:
                                if st.button("✕", key=f"btn_cert_del_{idx}", help="Delete Certification"):
                                    certs_list.pop(idx)
                                    res_data["certifications"] = certs_list
                                    st.session_state[res_session_key] = res_data
                                    st.rerun()

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                with st.expander("+ Add Certification Record", expanded=False):
                    with st.form("form_add_certification"):
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            new_c_name = st.text_input("Certification Name*", placeholder="AWS Certified Solutions Architect")
                            new_c_org = st.text_input("Issuing Organization*", placeholder="Amazon Web Services")
                            new_c_id = st.text_input("Credential ID", placeholder="AWS-892174")
                        with col_c2:
                            new_c_issue = st.text_input("Issue Date (YYYY-MM)", placeholder="2024-03")
                            new_c_noexp = st.checkbox("No Expiration", value=True)
                            new_c_exp = st.text_input("Expiry Date (YYYY-MM)", placeholder="2027-03", disabled=new_c_noexp)
                            new_c_url = st.text_input("Credential Verification URL", placeholder="https://aws.amazon.com/verify")

                        btn_submit_cert = st.form_submit_button("+ Add Certification", type="primary")
                        if btn_submit_cert:
                            if not new_c_name.strip() or not new_c_org.strip():
                                st.error("Certification name and issuing organization are required.")
                            elif new_c_url.strip() and not validate_url(new_c_url.strip()):
                                st.error(f"Invalid verification URL format: '{new_c_url.strip()}'.")
                            else:
                                if "certifications" not in res_data:
                                    res_data["certifications"] = []
                                res_data["certifications"].append({
                                    "id": f"cert_{len(res_data['certifications']) + 1}",
                                    "name": new_c_name.strip(),
                                    "issuing_org": new_c_org.strip(),
                                    "issue_date": new_c_issue.strip(),
                                    "expiry_date": "" if new_c_noexp else new_c_exp.strip(),
                                    "no_expiry": new_c_noexp,
                                    "credential_id": new_c_id.strip(),
                                    "credential_url": new_c_url.strip()
                                })
                                st.session_state[res_session_key] = res_data
                                st.success(f"Added certification '{new_c_name.strip()}'")
                                st.rerun()

            # --- SECTION F: PROJECTS ---
            with st.expander(f"Section F &bull; Projects & Key Achievements ({len(projs_list)} entries)", expanded=True):
                st.caption("Showcase major engineering deliverables, open-source work, and system designs.")

                if projs_list:
                    for idx, p in enumerate(projs_list):
                        with st.container(border=True):
                            col_p_head, col_p_ctrl = st.columns([5, 1])
                            with col_p_head:
                                role_lbl = f" ({p.get('role', '')})" if p.get('role') else ""
                                st.markdown(
                                    f"""
                                    <div style="font-weight: 800; font-size: 1.02rem; color: #0F172A;">{p.get('title', 'Project')}{role_lbl}</div>
                                    <div style="font-size: 0.83rem; color: #2563EB; font-weight: 600;">Tech: {p.get('technologies', 'N/A')}</div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                if p.get("description"):
                                    st.markdown(f"<div style='font-size: 0.87rem; color: #334155; margin-top: 4px; line-height: 1.45;'>{p['description']}</div>", unsafe_allow_html=True)
                                
                                p_urls = []
                                if p.get("project_url"):
                                    p_urls.append(f"<a href='{p['project_url']}' target='_blank' style='color: #2563EB;'>Live Demo</a>")
                                if p.get("github_url"):
                                    p_urls.append(f"<a href='{p['github_url']}' target='_blank' style='color: #2563EB;'>Source Code</a>")
                                if p_urls:
                                    st.markdown(f"<div style='font-size: 0.82rem; margin-top: 4px;'>{' &bull; '.join(p_urls)}</div>", unsafe_allow_html=True)
                            with col_p_ctrl:
                                if st.button("✕", key=f"btn_proj_del_{idx}", help="Delete Project"):
                                    projs_list.pop(idx)
                                    res_data["projects"] = projs_list
                                    st.session_state[res_session_key] = res_data
                                    st.rerun()

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                with st.expander("+ Add Project Entry", expanded=False):
                    with st.form("form_add_project"):
                        col_pr1, col_pr2 = st.columns(2)
                        with col_pr1:
                            new_p_title = st.text_input("Project Title*", placeholder="Cloud-Native Talent Platform")
                            new_p_role = st.text_input("Your Role", placeholder="Lead Architect / Developer")
                            new_p_tech = st.text_input("Technologies Used*", placeholder="Python, React, SQLite, Docker")
                        with col_pr2:
                            new_p_purl = st.text_input("Project / Demo URL", placeholder="https://example.com/demo")
                            new_p_ghurl = st.text_input("GitHub URL", placeholder="https://github.com/example/project")

                        new_p_desc = st.text_area("Project Description", placeholder="Engineered multi-tenant isolation, automated welcome email delivery, and ATS resume scoring.", height=85)
                        btn_submit_proj = st.form_submit_button("+ Add Project", type="primary")

                        if btn_submit_proj:
                            if not new_p_title.strip() or not new_p_tech.strip():
                                st.error("Project title and technologies used are required.")
                            elif new_p_purl.strip() and not validate_url(new_p_purl.strip()):
                                st.error(f"Invalid Project URL format: '{new_p_purl.strip()}'.")
                            elif new_p_ghurl.strip() and not validate_url(new_p_ghurl.strip()):
                                st.error(f"Invalid GitHub URL format: '{new_p_ghurl.strip()}'.")
                            else:
                                if "projects" not in res_data:
                                    res_data["projects"] = []
                                res_data["projects"].append({
                                    "id": f"proj_{len(res_data['projects']) + 1}",
                                    "title": new_p_title.strip(),
                                    "role": new_p_role.strip(),
                                    "technologies": new_p_tech.strip(),
                                    "project_url": new_p_purl.strip(),
                                    "github_url": new_p_ghurl.strip(),
                                    "description": new_p_desc.strip()
                                })
                                st.session_state[res_session_key] = res_data
                                st.success(f"Added project '{new_p_title.strip()}'")
                                st.rerun()

            # --- SECTION G: PROFESSIONAL LINKS ---
            with st.expander(f"Section G &bull; Professional Links ({len(links_list)} links)", expanded=True):
                st.caption("Public portfolio, LinkedIn profile, GitHub repositories, or technical blog.")

                if links_list:
                    for idx, l in enumerate(links_list):
                        col_l_lbl, col_l_url, col_l_del = st.columns([2, 5, 1])
                        with col_l_lbl:
                            st.markdown(f"**{l.get('label', 'Link')}**")
                        with col_l_url:
                            l_target = l.get('url', '')
                            href = l_target if l_target.startswith('http') else f"https://{l_target}"
                            st.markdown(f"<a href='{href}' target='_blank' style='color: #2563EB;'>{l_target}</a>", unsafe_allow_html=True)
                        with col_l_del:
                            if st.button("✕", key=f"btn_link_del_{idx}", help="Remove Link"):
                                links_list.pop(idx)
                                res_data["links"] = links_list
                                st.session_state[res_session_key] = res_data
                                st.rerun()

                st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
                with st.expander("+ Add Professional Link", expanded=False):
                    with st.form("form_add_link"):
                        col_lk1, col_lk2 = st.columns([2.5, 4.5])
                        with col_lk1:
                            new_l_label = st.selectbox("Platform / Label", ["LinkedIn", "GitHub", "Portfolio", "Personal Website", "Blog", "Other"])
                        with col_lk2:
                            new_l_url = st.text_input("URL Address*", placeholder="https://linkedin.com/in/username")

                        btn_submit_link = st.form_submit_button("+ Add Link", type="primary")
                        if btn_submit_link:
                            if not new_l_url.strip():
                                st.error("Please enter a web URL.")
                            elif not validate_url(new_l_url.strip()):
                                st.error(f"Invalid URL format: '{new_l_url.strip()}'. Must be a valid HTTP/HTTPS address or domain.")
                            else:
                                if "links" not in res_data:
                                    res_data["links"] = []
                                res_data["links"].append({
                                    "id": f"link_{len(res_data['links']) + 1}",
                                    "label": new_l_label,
                                    "url": new_l_url.strip()
                                })
                                st.session_state[res_session_key] = res_data
                                st.success(f"Added link '{new_l_label}'")
                                st.rerun()

            # --- GLOBAL SAVE ACTION BAR ---
            st.markdown("<div style='border-top: 2px solid #E2E8F0; margin: 2rem 0 1.25rem 0;'></div>", unsafe_allow_html=True)
            col_save_btn, col_cancel_btn, col_save_status = st.columns([3, 2, 4])
            with col_save_btn:
                if st.button("💾 Save All Resume Changes", key="btn_rs_save_all", type="primary", use_container_width=True):
                    ok_save, msg_save = save_resume(active_target_uid, res_data, org_id=org_id)
                    if ok_save:
                        st.session_state[res_session_key] = get_resume(active_target_uid, org_id=org_id) or {}
                        # Refresh global profile and skills
                        st.session_state.profile = get_profile(active_target_uid)
                        st.session_state.skills = list_skills(active_target_uid)
                        st.success("All resume changes successfully persisted to database!")
                        st.rerun()
                    else:
                        st.error(f"Save failed: {msg_save}")
            with col_cancel_btn:
                if st.button("Cancel & Revert", key="btn_rs_cancel_changes", type="secondary", use_container_width=True):
                    st.session_state[res_session_key] = get_resume(active_target_uid, org_id=org_id) or {}
                    st.info("Reverted unsaved changes to previously saved database state.")
                    st.rerun()
            with col_save_status:
                last_updated = res_data.get("updated_at", "Just now")
                st.caption(f"Status: Database connected &bull; Last synchronized: {last_updated}")

    # ==========================================================================
    # TAB 2: ATS RESUME PREVIEW & PDF EXPORT
    # ==========================================================================
    with tab_preview:
        col_prev_head, col_prev_pdf = st.columns([5, 3])
        with col_prev_head:
            st.markdown("<h3 style='font-size: 1.25rem; font-weight: 800; color: #0F172A; margin: 0.5rem 0 0.2rem 0;'>ATS Resume Live Preview</h3>", unsafe_allow_html=True)
            st.caption("Structured, applicant-tracking-system compliant layout generated from your saved resume database records.")
        with col_prev_pdf:
            pdf_bytes = generate_resume_pdf(
                res_data,
                {
                    "name": active_target_user.get("name", "User"),
                    "email": active_target_user.get("email", ""),
                    "phone": active_target_profile.get("phone", ""),
                    "location": active_target_profile.get("location", "")
                }
            )
            st.download_button(
                "📥 Download ATS Resume PDF",
                pdf_bytes,
                file_name=f"talent_growth_resume_{active_target_user.get('employee_id', active_target_uid)}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key=f"btn_dl_resume_pdf_{active_target_uid}"
            )

        # Contact Links string
        preview_links_list = [f'<a href="{l["url"] if l["url"].startswith("http") else "https://" + l["url"]}" class="ts-resume-contact-link" target="_blank">{l["label"]}</a>' for l in links_list]
        contact_line_parts = []
        if active_target_user.get("email"):
            contact_line_parts.append(f'<a href="mailto:{active_target_user.get("email")}" class="ts-resume-contact-link">{active_target_user.get("email")}</a>')
        if active_target_profile.get("phone"):
            contact_line_parts.append(f"<span>{active_target_profile.get('phone', '')}</span>")
        if active_target_profile.get("location"):
            contact_line_parts.append(f"<span>{active_target_profile.get('location', '')}</span>")
        contact_line_parts.extend(preview_links_list)

        # ATS Paper Render
        render_html(
            f"""
            <div class="ts-resume-paper">
                <div class="ts-resume-header-name">{active_target_user.get('name', 'User')}</div>
                <div style="font-size: 0.92rem; color: #475569; margin-bottom: 1.25rem;">
                    {' &nbsp;&bull;&nbsp; '.join(contact_line_parts)}
                </div>

                {f'''
                <div class="ts-resume-section-heading">Professional Summary</div>
                <div class="ts-resume-section-text">{summary_txt}</div>
                ''' if summary_txt else ''}

                {f'''
                <div class="ts-resume-section-heading">Core Competencies &amp; Skills</div>
                <div class="ts-resume-section-text">{', '.join(f"<strong>{s['name']}</strong> ({s.get('proficiency', 'Proficient')})" for s in skills_list)}</div>
                ''' if skills_list else ''}

                {f'''
                <div class="ts-resume-section-heading">Professional Experience</div>
                ''' if exp_list else ''}
                {''.join([f'''
                <div style="margin-bottom: 0.85rem;">
                    <div style="display: flex; justify-content: space-between; font-weight: 700; color: #0F172A; font-size: 0.98rem;">
                        <span>{e.get('job_title', 'Role')} &mdash; <span style="color: #2563EB;">{e.get('company', 'Company')}</span></span>
                        <span style="font-size: 0.84rem; color: #64748B;">{e.get('start_date', '')} &ndash; {e.get('end_date', 'Present')}</span>
                    </div>
                    {f'<div style="font-size: 0.82rem; color: #64748B; margin-bottom: 2px;">{e.get("location")}</div>' if e.get("location") else ''}
                    <div class="ts-resume-section-text" style="margin-top: 2px;">{e.get('description', '')}</div>
                </div>
                ''' for e in exp_list])}

                {f'''
                <div class="ts-resume-section-heading">Education</div>
                ''' if edu_list else ''}
                {''.join([f'''
                <div style="margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; font-weight: 700; color: #0F172A; font-size: 0.96rem;">
                        <span>{ed.get('degree', 'Degree')} &mdash; {ed.get('institution', 'Institution')}</span>
                        <span style="font-size: 0.84rem; color: #64748B;">{ed.get('start_date', '')} &ndash; {ed.get('end_date', '')}</span>
                    </div>
                    {f'<div class="ts-resume-section-text">{ed.get("details")}</div>' if ed.get("details") else ''}
                </div>
                ''' for ed in edu_list])}

                {f'''
                <div class="ts-resume-section-heading">Certifications &amp; Credentials</div>
                ''' if certs_list else ''}
                {''.join([f'''
                <div style="font-size: 0.9rem; color: #334155; margin-bottom: 4px;">
                    &bull; <strong>{c.get('name', '')}</strong> &mdash; {c.get('issuing_org', '')} ({c.get('issue_date', '')})
                    {f' [ID: {c.get("credential_id")}]' if c.get("credential_id") else ''}
                </div>
                ''' for c in certs_list])}

                {f'''
                <div class="ts-resume-section-heading">Projects &amp; Achievements</div>
                ''' if projs_list else ''}
                {''.join([f'''
                <div style="margin-bottom: 0.85rem;">
                    <div style="font-weight: 700; color: #0F172A; font-size: 0.96rem;">{p.get('title', 'Project')} {f"({p.get('role')})" if p.get('role') else ""}</div>
                    {f'<div style="font-size: 0.82rem; color: #2563EB; font-weight: 600;">Technologies: {p.get("technologies")}</div>' if p.get("technologies") else ''}
                    <div class="ts-resume-section-text" style="margin-top: 2px;">{p.get('description', '')}</div>
                </div>
                ''' for p in projs_list])}
            </div>
            """
        )

        # Upload existing resume text import for alignment evaluation
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        with st.expander("Import Existing PDF or DOCX Resume (Text Extractor)", expanded=False):
            upload = st.file_uploader("Import a PDF or DOCX resume file", type=["pdf", "docx"], key=f"rs_uploader_{active_target_uid}")
            if upload:
                try:
                    if upload.name.lower().endswith(".pdf"):
                        extracted_txt = "\n".join(p.extract_text() or "" for p in PdfReader(upload).pages)
                    else:
                        extracted_txt = "\n".join(p.text for p in Document(upload).paragraphs)
                    save_profile(active_target_uid, {"resume_text": extracted_txt})
                    st.success("Resume text extracted and saved for ATS alignment audits.")
                except Exception as exc:
                    st.error(f"Could not read file: {exc}")

    # ==========================================================================
    # TAB 3: AI ATS SCREENER & BULLET OPTIMIZER
    # ==========================================================================
    with tab_screener:
        render_html(
            f"""
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.1rem 1.4rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 8px;">
                        {get_svg_icon("sparkles", size=20, color="#2563EB")} AI Resume Auditor & Bullet Rewriter (Gemini & Heuristic)
                    </div>
                    <div style="color: #64748B; font-size: 0.88rem; margin-top: 3px;">
                        Deep ATS screening, passive voice detection, and Google XYZ / STAR format bullet rewriting.
                    </div>
                </div>
                <div>
                    <span class="badge-status badge-active">AI OPTIMIZER</span>
                </div>
            </div>
            """
        )

        col_audit_btn, col_audit_opt = st.columns([2.5, 3.5])
        with col_audit_btn:
            audit_clicked = st.button("Run Deep AI Resume & Bullet Audit", type="primary", use_container_width=True, key=f"btn_run_ai_audit_{active_target_uid}")
        with col_audit_opt:
            audit_source = st.radio("Audit Content Source", ["Structured Resume Editor Content", "Uploaded Resume File Text"], horizontal=True, key=f"rs_audit_source_radio_{active_target_uid}")

        if audit_clicked:
            if audit_source == "Structured Resume Editor Content":
                resume_source_text = format_resume_as_text(res_data, active_target_user)
            else:
                resume_source_text = active_target_profile.get("resume_text", "")
                if not resume_source_text.strip():
                    resume_source_text = format_resume_as_text(res_data, active_target_user)

            if not resume_source_text.strip():
                st.warning("Please populate your resume in the editor or upload an existing resume file to run the audit.")
            else:
                target_role = active_target_profile.get("target_role", "Senior Software Engineer")
                target_skills_list = list(ROLE_CATALOG.get(target_role, {}).get("skills", {}).keys())

                with st.spinner("Running deep AI ATS audit and STAR bullet optimization..."):
                    audit_res = analyze_resume_with_ai(
                        resume_text=resume_source_text,
                        target_role=target_role,
                        target_skills=target_skills_list,
                        profile=active_target_profile,
                        api_key=st.session_state.get("gemini_user_key")
                    )
                    st.session_state[f"last_resume_audit_{active_target_uid}"] = audit_res

        audit_key = f"last_resume_audit_{active_target_uid}"
        if audit_key in st.session_state:
            res = st.session_state[audit_key]
            ats_score = res.get("ats_score", 75)
            score_color = "#10B981" if ats_score >= 80 else ("#F59E0B" if ats_score >= 60 else "#EF4444")

            render_html(
                f"""
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; margin: 1.25rem 0 1rem 0;">
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 12px 14px; border-radius: 10px;">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">ATS Match Score</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: {score_color};">{ats_score} / 100</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 12px 14px; border-radius: 10px;">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Keywords Matched</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #2563EB;">{len(res.get("detected_keywords", []))} Detected</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 12px 14px; border-radius: 10px;">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Keywords Missing</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #EF4444;">{len(res.get("missing_keywords", []))} High Priority</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 12px 14px; border-radius: 10px;">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Action Verbs</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #10B981;">{len(res.get("strong_action_verbs_found", []))} Strong</div>
                    </div>
                </div>
                """
            )

            with st.container(border=True):
                st.markdown(f"**Executive Recruiter Summary:**\n\n{res.get('alignment_summary', '')}")

            bullets = res.get("bullet_optimizations", [])
            if bullets:
                render_html(
                    f"""
                    <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.25rem 0 0.75rem 0;">
                        {get_svg_icon("target", size=18, color="#2563EB")} AI Rewritten Bullet Points (STAR Format)
                    </div>
                    """
                )
                for b_idx, b in enumerate(bullets, 1):
                    with st.container(border=True):
                        col_orig, col_opt = st.columns(2)
                        with col_orig:
                            st.markdown(f"**Original Bullet #{b_idx}:**")
                            st.markdown(f"> *{b.get('original_bullet', '')}*")
                        with col_opt:
                            st.markdown(f"**High-Impact STAR Rewrite:**")
                            st.markdown(f"> **{b.get('rewritten_bullet', '')}**")
                        if b.get("improvement_reason"):
                            st.caption(f"Reasoning: {b.get('improvement_reason')}")

            weak_phrases = res.get("weak_phrases_to_replace", [])
            if weak_phrases:
                with st.expander("Weak & Passive Phrases to Upgrade", expanded=True):
                    for wp in weak_phrases:
                        c_old, c_new = st.columns(2)
                        c_old.markdown(f'<span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: #FEE2E2; color: #991B1B; font-weight: 700; font-size: 0.74rem; margin-right: 6px;">WEAK</span> *"{wp.get("original", "")}"*', unsafe_allow_html=True)
                        c_new.markdown(f'<span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: #DCFCE7; color: #166534; font-weight: 700; font-size: 0.74rem; margin-right: 6px;">RECOMMENDED</span> **"{wp.get("suggested", "")}"**', unsafe_allow_html=True)

            recs = res.get("top_recommendations", [])
            if recs:
                render_html(
                    f"""
                    <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.25rem 0 0.75rem 0;">
                        {get_svg_icon("clipboard", size=18, color="#2563EB")} High-Leverage Resume Optimizations
                    </div>
                    """
                )
                for r in recs:
                    st.markdown(f"- {r}")

            if res.get("source") == "gemini":
                st.success(f"AI Resume Audit generated live via Google Gemini (`{res.get('model')}`).")
            else:
                st.info("Audit generated via deterministic heuristic engine. Add Gemini API Key for dynamic neural audits.")


# ==============================================================================
# 10. CAREER DIRECTION & AI COACH
# ==============================================================================
elif page in ["Career Direction", "Career Direction & Gaps"]:
    st.markdown("<h1 style='font-size: 2.1rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em; margin-bottom: 1.5rem;'>Career direction</h1>", unsafe_allow_html=True)

    with st.form("career_direction_form"):
        current = st.text_input("Current role", value=profile.get("job_title", ""))
        roles_list = ["Choose a role"] + list(ROLE_CATALOG.keys())
        curr_role_idx = (roles_list.index(profile["target_role"])) if profile.get("target_role") in ROLE_CATALOG else 0
        target = st.selectbox("Target role", roles_list, index=curr_role_idx)

        levels = ["Senior", "Lead", "Manager", "Director", "Principal", "Individual contributor"]
        curr_lvl_idx = levels.index(profile.get("target_level")) if profile.get("target_level") in levels else 0
        level = st.selectbox("Target level", levels, index=curr_lvl_idx)

        timelines = ["3–6 months", "6–12 months", "1–2 years", "Exploring"]
        curr_time_idx = timelines.index(profile.get("timeline")) if profile.get("timeline") in timelines else 0
        timeline = st.selectbox("Target timeline", timelines, index=curr_time_idx)

        industry = st.text_input("Target industry", value=profile.get("target_industry", ""))
        goal = st.text_area("What does career growth mean to you?", value=profile.get("career_goal", ""), height=100)

        submit_dir = st.form_submit_button("Save career direction", type="primary")

        if submit_dir:
            save_profile(uid, {
                "job_title": current,
                "target_role": "" if target == "Choose a role" else target,
                "target_level": level,
                "timeline": timeline,
                "target_industry": industry,
                "career_goal": goal
            })
            st.success("Career direction saved successfully!")
            st.rerun()

    if profile.get("target_role") and profile.get("target_role") in ROLE_CATALOG:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.info(f"**Benchmark Standard Criteria for {profile['target_role']}:** {ROLE_CATALOG[profile['target_role']]['criteria']}")

elif page in ["Career Coach", "AI Career Coach"]:
    # Check Gemini API status
    current_key = get_gemini_api_key(st.session_state.get("gemini_user_key"))
    has_gemini = bool(current_key)
    badge_label = "GEMINI LIVE AI ACTIVE" if has_gemini else "DETERMINISTIC HEURISTIC MODE"
    badge_color = "#10B981" if has_gemini else "#64748B"
    badge_bg = "#ECFDF5" if has_gemini else "#F1F5F9"
    badge_border = "#A7F3D0" if has_gemini else "#CBD5E1"

    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("coach", size=24, color="#8B5CF6")} AI Career Strategy Coach & Executive Advisor
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Data-driven career guidance evaluating competency matrix gaps, promotion trajectories, and role readiness.
                </div>
            </div>
            <div>
                <span style="display: inline-flex; align-items: center; gap: 6px; background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color}; padding: 5px 12px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;">
                    <span style="width: 7px; height: 7px; background: {badge_color}; border-radius: 50%;"></span>
                    {badge_label}
                </span>
            </div>
        </div>
        """
    )

    with st.expander("Gemini API Configuration & Model Settings", expanded=(not has_gemini)):
        st.caption("Powered by Google Gemini API. Set your key in `.env` (`GEMINI_API_KEY=your_key`) or paste it below for live generative coaching.")
        col_k1, col_k2 = st.columns([3, 1])
        with col_k1:
            entered_key = st.text_input("Gemini API Key", value=st.session_state.get("gemini_user_key", current_key or ""), type="password", placeholder="AIzaSy...", help="Get a free key from Google AI Studio (aistudio.google.com)")
        with col_k2:
            st.write("")
            st.write("")
            if st.button("Save API Key", use_container_width=True, type="secondary"):
                if entered_key.strip():
                    st.session_state.gemini_user_key = entered_key.strip()
                    st.success("API Key saved for current session!")
                    st.rerun()
                else:
                    st.session_state.gemini_user_key = ""
                    st.info("Cleared session API key.")
                    st.rerun()

    render_html(
        f"""
        <div style="font-size: 1.1rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.25rem 0 0.75rem 0;">
            {get_svg_icon("lightbulb", size=18, color="#2563EB")} Quick Strategy Prompts (1-Click Analysis)
        </div>
        """
    )
    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        if st.button("Lead Role Roadmap", use_container_width=True):
            st.session_state.coach_prompt_val = "What precise strategic roadmap should I follow to advance into a Lead / Principal designation over the next 12 months?"
    with cp2:
        if st.button("Cloud & Architecture", use_container_width=True):
            st.session_state.coach_prompt_val = "Which high-leverage cloud and distributed architecture skills will maximize my competency valuation?"
    with cp3:
        if st.button("Promotion Blueprint", use_container_width=True):
            st.session_state.coach_prompt_val = "How should I structure my achievements and metrics for our upcoming annual performance review cycle?"
    with cp4:
        if st.button("90-Day Action Plan", use_container_width=True):
            st.session_state.coach_prompt_val = "Generate a prioritized 90-day developmental sprint to close my most pressing skill gap."

    default_q = st.session_state.get("coach_prompt_val", "")
    question = st.text_area("Your Career Strategy Question:", value=default_q, placeholder="e.g. What specific competencies should I master to transition into a Lead Cloud Architect position?")
    
    if st.button("Generate Executive Strategy Guidance", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please select a quick prompt above or enter your career question.")
        else:
            a = analysis_bundle()
            gaps_info = gap_analysis(profile.get("target_role", "Software Engineer"), skills)
            target_role = profile.get("target_role", "Senior Engineer")
            
            with st.spinner("Consulting AI Career Coach (evaluating profile benchmarks and skill gaps)..."):
                advice_res = generate_ai_coaching_guidance(
                    user_name=user.get("name", "User"),
                    question=question,
                    profile=profile,
                    skills=skills,
                    target_role=target_role,
                    gap_data=gaps_info,
                    api_key=st.session_state.get("gemini_user_key")
                )
            
            # Metrics Row
            render_html(
                f"""
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.5rem 0 1rem 0;">
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 14px 18px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Profile Strength</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #2563EB;">{a['score']} / 100</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 14px 18px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Target Role Alignment</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #10B981;">{a['match']}%</div>
                    </div>
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; padding: 14px 18px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                        <div style="font-size: 0.72rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Identified Competency Gaps</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #F59E0B;">{len(gaps_info)} Competencies</div>
                    </div>
                </div>
                """
            )

            # Advice Body
            with st.container(border=True):
                st.markdown(advice_res["content"])
            
            if advice_res["source"] == "gemini":
                st.success(f"Generated live via Google Gemini (`{advice_res['model']}`) based on your verified skills, experience, and target benchmarks.")
            elif advice_res["source"] == "offline_fallback":
                st.warning(f"Live Gemini API could not be reached ({advice_res['error']}). Displaying rule-based strategic blueprint.")
            else:
                st.info("Displayed in deterministic heuristic mode. Add your Gemini API key in the configuration above to unlock real-time generative coaching.")

# ==============================================================================
# 11. SETTINGS & SYSTEM
# ==============================================================================
elif page in ["Settings", "Settings & System", "Settings & Privacy"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("settings", size=24, color="#475569")} System Settings & Data Governance
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Manage local database persistence, role-based access controls, and data exports.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">SYSTEM GOVERNANCE</span>
            </div>
        </div>
        """
    )

    db_health = check_db_health()
    db_status_color = "#10B981" if db_health["connected"] else "#EF4444"
    db_status_text = "CONNECTED & PERSISTING" if db_health["connected"] else "ATTENTION NEEDED"

    st.write(f"Logged in as: **{user.get('name', 'User')}** (`{user.get('email', '')}`) · Role: `{user.get('role', 'employee').upper()}`")

    render_html(
        f"""
        <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.25rem 0 0.75rem 0;">
            {get_svg_icon("database", size=20, color="#2563EB")} SQLite Database Connection & Storage
        </div>
        """
    )
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem; margin-bottom: 1.25rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="width: 10px; height: 10px; background: {db_status_color}; border-radius: 50%; display: inline-block;"></span>
                    <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">{db_health['filename']}</span>
                </div>
                <span style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; font-size: 0.74rem; font-weight: 800; padding: 3px 10px; border-radius: 9999px;">
                    {db_status_text}
                </span>
            </div>
            <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 8px;">
                Active Storage Path:
            </div>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px 12px; font-family: monospace; font-size: 0.85rem; color: #0F172A; word-break: break-all; margin-bottom: 12px;">
                {db_health['path']}
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px;">
                <div style="background: #F1F5F9; border-radius: 8px; padding: 8px 12px; text-align: center;">
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase;">Database Size</div>
                    <div style="font-weight: 800; color: #0F172A; font-size: 1rem;">{db_health['size_kb']} KB</div>
                </div>
                <div style="background: #F1F5F9; border-radius: 8px; padding: 8px 12px; text-align: center;">
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase;">Employees</div>
                    <div style="font-weight: 800; color: #2563EB; font-size: 1rem;">{db_health['counts'].get('employees', 0)}</div>
                </div>
                <div style="background: #F1F5F9; border-radius: 8px; padding: 8px 12px; text-align: center;">
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase;">Reviews</div>
                    <div style="font-weight: 800; color: #10B981; font-size: 1rem;">{db_health['counts'].get('performance_reviews', 0)}</div>
                </div>
                <div style="background: #F1F5F9; border-radius: 8px; padding: 8px 12px; text-align: center;">
                    <div style="font-size: 0.72rem; color: #64748B; text-transform: uppercase;">Career Goals</div>
                    <div style="font-weight: 800; color: #F59E0B; font-size: 1rem;">{db_health['counts'].get('career_goals', 0)}</div>
                </div>
            </div>
        </div>
        """
    )

    col_db_act1, col_db_act2 = st.columns(2)
    with col_db_act1:
        if st.button("Run PRAGMA Integrity Check", use_container_width=True):
            st.success(f"Database Integrity Result: **{db_health['integrity'].upper()}** · Foreign Keys: ON · ACID Compliant")
    with col_db_act2:
        db_path = get_db_path()
        if db_path.is_file():
            with open(db_path, "rb") as f:
                db_bytes = f.read()
            st.download_button("Download Database (talentgrowth.db)", db_bytes, file_name="talentgrowth.db", mime="application/octet-stream", use_container_width=True)

    render_html(
        f"""
        <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.5rem 0 0.75rem 0;">
            {get_svg_icon("download", size=20, color="#2563EB")} Export System Data Snapshot
        </div>
        """
    )
    payload = json.dumps(export_user_data(uid), indent=2, default=str).encode("utf-8")
    st.download_button("Download Complete System Snapshot (JSON)", payload, file_name="talent_growth_snapshot.json", mime="application/json", type="primary")
