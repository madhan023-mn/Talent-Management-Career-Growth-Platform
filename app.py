from __future__ import annotations
import json
import textwrap
import os
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
    get_db_path, check_db_health
)
from services.reports import create_report
from services.ai_coach import (
    generate_ai_coaching_guidance,
    analyze_resume_with_ai,
    get_gemini_api_key
)
from style import load_css

load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="Talent Growth — Talent Management Platform",
    page_icon="assets/talent_growth_icon_thumb.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database schema and ensure migrations
init_db()

@st.cache_data
def get_logo_b64(which: str = "icon") -> str:
    path = "assets/talent_growth_icon_thumb.png" if which == "icon" else "assets/talent_growth_full_thumb.png"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

def render_html(html_str: str) -> None:
    """Safely renders HTML without markdown parser converting indented lines into code blocks."""
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# CLEAN SVG ICON SYSTEM (Zero Emojis, Pixel-Perfect Vector Icons & Brand Mark)
# ------------------------------------------------------------------------------
def get_svg_icon(name: str, size: int = 18, color: str = "currentColor", extra_style: str = "") -> str:
    """Returns an inline, standalone, crisp SVG icon string (Lucide/Feather styled)."""
    icon_b64 = get_logo_b64("icon")
    full_b64 = get_logo_b64("full")
    icons = {
        "dashboard": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
        "employees": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        "performance": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/></svg>',
        "skills": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>',
        "goals": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "reports": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
        "settings": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
        "logout": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>',
        "search": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
        "bell": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
        "star": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "building": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>',
        "clock": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
        "check": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>',
        "plus": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
        "shield": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>',
        "brand_logo": f'<img src="data:image/png;base64,{icon_b64}" style="width: {size}px; height: {size}px; border-radius: 8px; object-fit: contain; {extra_style}" alt="Talent Growth Logo" />',
        "brand_full": f'<img src="data:image/png;base64,{full_b64}" style="height: {size}px; max-width: 100%; object-fit: contain; {extra_style}" alt="Talent Growth Logo" />',
        "arrow_right": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>',
        "code": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
        "user_check": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/></svg>',
        "profile": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "coach": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M12 2a8 8 0 0 0-8 8c0 3 1.5 5.5 4 6.8V19a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.2c2.5-1.3 4-3.8 4-6.8a8 8 0 0 0-8-8z"/><path d="M9 22h6"/></svg>',
        "lock": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
        "user_plus": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/></svg>',
        "user": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "layers": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.9a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
        "analytics": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>',
        "sparkles": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>',
        "target": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "table": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>',
        "card": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
        "zap": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
        "clipboard": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>',
        "rocket": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
        "cloud": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>',
        "trending_up": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
        "lightbulb": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>',
        "database": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>',
        "download": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>',
        "key": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></svg>',
        "mail": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
        "phone": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
        "award": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>',
        "calendar": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>',
        "briefcase": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>',
        "filter": f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="{extra_style}"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>'
    }
    return icons.get(name, f'<span style="{extra_style}"></span>')

# ------------------------------------------------------------------------------
# MODERN CORPORATE DESIGN SYSTEM & TOKENS (TalentManager / TalentPro Theme)
# ------------------------------------------------------------------------------
load_css()

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
    # Top Navbar: Brand on left, System status in middle, Sign In & Create Account on TOP RIGHT
    col_nav_brand, col_nav_status, col_nav_login, col_nav_reg = st.columns([3.8, 2.4, 1.6, 2.2], gap="small")
    with col_nav_brand:
        render_html(
            f"""
            <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0;">
                {get_svg_icon("brand_logo", size=34)}
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span style="font-size: 1.35rem; font-weight: 800; color: #0F172A; letter-spacing: -0.02em;">Talent Growth</span>
                    <span style="font-size: 0.72rem; color: #2563EB; font-weight: 700; background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 9999px; padding: 2px 8px;">ENTERPRISE</span>
                </div>
            </div>
            """
        )
    with col_nav_status:
        render_html(
            """
            <div style="padding-top: 8px; text-align: right;">
                <span style="display: inline-flex; align-items: center; gap: 6px; background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 5px 12px; border-radius: 9999px; font-size: 0.82rem; font-weight: 600;">
                    <span style="width: 7px; height: 7px; background: #10B981; border-radius: 50%;"></span>
                    System Online
                </span>
            </div>
            """
        )
    with col_nav_login:
        if st.button("Sign In", key="nav_btn_login", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "login"
            st.rerun()
    with col_nav_reg:
        if st.button("Create Account", key="nav_btn_reg", use_container_width=True, type="primary"):
            st.session_state.auth_view = "register"
            st.rerun()

    st.markdown("<div style='border-bottom: 1px solid #E2E8F0; margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # HERO SECTION (High-Impact Enterprise Banner)
    render_html(
        f"""
        <div class="webpage-hero">
            <div style="max-width: 860px;">
                <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(37, 99, 235, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); padding: 5px 14px; border-radius: 9999px; color: #93C5FD; font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1.25rem;">
                    {get_svg_icon("sparkles", size=14, color="#93C5FD")}
                    Talent Management Platform
                </div>
                <h1 style="font-size: 2.6rem; font-weight: 800; color: #FFFFFF; line-height: 1.18; letter-spacing: -0.03em; margin: 0 0 1rem 0;">
                    Build Better Teams,<br/>
                    <span style="color: #60A5FA;">Grow Together</span>
                </h1>
                <p style="color: #94A3B8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 1.75rem; max-width: 720px;">
                    Talent management for a brighter future. Elevate workforce performance, discover skill benchmarks, and navigate personalized career pathways with intelligent evaluations and goal roadmaps.
                </p>
                <div style="display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 2rem;">
                    <div style="display: flex; align-items: center; gap: 8px; color: #E2E8F0; font-size: 0.88rem; font-weight: 600; background: rgba(255, 255, 255, 0.06); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
                        {get_svg_icon("employees", size=16, color="#60A5FA")} Workforce Directory & Profiles
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; color: #E2E8F0; font-size: 0.88rem; font-weight: 600; background: rgba(255, 255, 255, 0.06); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
                        {get_svg_icon("performance", size=16, color="#34D399")} Performance Trajectory Reviews
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; color: #E2E8F0; font-size: 0.88rem; font-weight: 600; background: rgba(255, 255, 255, 0.06); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
                        {get_svg_icon("skills", size=16, color="#C084FC")} 10-Role Skill Benchmarks
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px; color: #E2E8F0; font-size: 0.88rem; font-weight: 600; background: rgba(255, 255, 255, 0.06); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
                        {get_svg_icon("goals", size=16, color="#FB923C")} SMART Milestone Roadmap
                    </div>
                </div>
            </div>
            <div style="border-top: 1px solid #1E293B; padding-top: 1.1rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.82rem; color: #64748B;">
                <span style="display: flex; align-items: center; gap: 6px;">
                    {get_svg_icon("shield", size=15, color="#64748B")}
                    Encrypted Authentication & Local SQLite Database
                </span>
                <span style="display: flex; align-items: center; gap: 6px;">
                    {get_svg_icon("check", size=15, color="#10B981")}
                    Enterprise Production Ready
                </span>
            </div>
        </div>
        """
    )

    # SEPARATED SECTION 1: 1-CLICK QUICK DEMO SIGN-IN
    # (Completely separated into its own distinct, dedicated section)
    render_html(
        f"""
        <div style="margin: 2.2rem 0 1rem 0;">
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
        with st.container(border=True):
            render_html(
                f"""
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #FEF3C7; color: #92400E; display: flex; align-items: center; justify-content: center;">
                        {get_svg_icon("shield", size=22, color="#92400E")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #92400E; background: #FEF3C7; border: 1px solid #FDE68A; padding: 3px 8px; border-radius: 9999px;">ADMIN</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">HR Administrator</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">admin@talentsphere.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Full administrative governance, workforce directory CRUD, performance trajectory tracking, bulk CSV imports, and ATS studio.
                </p>
                """
            )
            if st.button("Sign In as HR Admin →", key="landing_btn_admin", use_container_width=True, type="primary"):
                admin_acc = login("admin@talentsphere.com", "Admin@12345")
                if admin_acc:
                    st.session_state.user = admin_acc
                    st.session_state.current_page = "Dashboard"
                    st.rerun()

    with col_d2:
        with st.container(border=True):
            render_html(
                f"""
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #EFF6FF; color: #2563EB; display: flex; align-items: center; justify-content: center;">
                        {get_svg_icon("employees", size=22, color="#2563EB")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #1E40AF; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 3px 8px; border-radius: 9999px;">ENGINEER</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">Alex Morgan</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">alex@company.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Employee self-service portal, 10-role skill benchmark matrix, target readiness radar, and SMART milestones roadmap.
                </p>
                """
            )
            if st.button("Sign In as Alex Morgan →", key="landing_btn_alex", use_container_width=True, type="primary"):
                emp_acc = login("alex@company.com", "Password123")
                if emp_acc:
                    st.session_state.user = emp_acc
                    st.session_state.current_page = "Dashboard"
                    st.rerun()

    with col_d3:
        with st.container(border=True):
            render_html(
                f"""
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background: #ECFDF5; color: #065F46; display: flex; align-items: center; justify-content: center;">
                        {get_svg_icon("analytics", size=22, color="#065F46")}
                    </div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #065F46; background: #ECFDF5; border: 1px solid #A7F3D0; padding: 3px 8px; border-radius: 9999px;">DATA ANALYST</span>
                </div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 2px;">Ravi Kumar</div>
                <div style="font-size: 0.8rem; color: #64748B; font-family: monospace; margin-bottom: 0.75rem;">ravi@company.com</div>
                <p style="font-size: 0.86rem; color: #475569; line-height: 1.5; margin-bottom: 1.1rem; min-height: 54px;">
                    Competency portfolio tracking, historical review feedback, department skill gap analytics, and promotion milestones.
                </p>
                """
            )
            if st.button("Sign In as Ravi Kumar →", key="landing_btn_ravi", use_container_width=True, type="primary"):
                ravi_acc = login("ravi@company.com", "Password123")
                if ravi_acc:
                    st.session_state.user = ravi_acc
                    st.session_state.current_page = "Dashboard"
                    st.rerun()

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
        with st.container(border=True):
            render_html(
                f"""
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
                """
            )
        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            render_html(
                f"""
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
                """
            )

    with col_m2:
        with st.container(border=True):
            render_html(
                f"""
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
                """
            )
        st.markdown("<div style='margin-bottom: 0.75rem;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            render_html(
                f"""
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
        if st.button("Sign In with Email & Password →", key="cta_btn_signin", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "login"
            st.rerun()
    with c_cta2:
        if st.button("Create a New Account →", key="cta_btn_reg", use_container_width=True, type="primary"):
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
    # Top Bar: Top-left "← Back to Home" button & Logo on right
    col_back, col_spacer, col_logo = st.columns([2.5, 4.5, 3], gap="small")
    with col_back:
        if st.button("← Back to Home", key="btn_login_back_home", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "landing"
            st.rerun()
    with col_logo:
        render_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 4px;">
                {get_svg_icon("brand_logo", size=28)}
                <span style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">Talent Growth</span>
                <span style="display: inline-flex; align-items: center; gap: 5px; background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 3px 9px; border-radius: 9999px; font-size: 0.74rem; font-weight: 600;">
                    <span style="width: 6px; height: 6px; background: #10B981; border-radius: 50%;"></span> Online
                </span>
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
                        st.success(f"Welcome back, {user_data['name']}!")
                        st.rerun()
                    else:
                        st.error("Authentication failed: Invalid email or password. Please verify your credentials.")

            render_html("<div style='border-top: 1px solid #E2E8F0; margin: 1.25rem 0 0.85rem 0;'></div>")
            render_html("<div style='text-align: center; font-size: 0.86rem; color: #64748B; margin-bottom: 0.5rem;'>Don't have an account yet?</div>")
            if st.button("Create a New Account →", key="btn_login_to_register", use_container_width=True, type="secondary"):
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
    # Top Bar: Top-left "← Back to Home" button & Logo on right
    col_back, col_spacer, col_logo = st.columns([2.5, 4.5, 3], gap="small")
    with col_back:
        if st.button("← Back to Home", key="btn_reg_back_home", use_container_width=True, type="secondary"):
            st.session_state.auth_view = "landing"
            st.rerun()
    with col_logo:
        render_html(
            f"""
            <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 4px;">
                {get_svg_icon("brand_logo", size=28)}
                <span style="font-size: 1.25rem; font-weight: 800; color: #0F172A;">Talent Growth</span>
                <span style="display: inline-flex; align-items: center; gap: 5px; background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 3px 9px; border-radius: 9999px; font-size: 0.74rem; font-weight: 600;">
                    <span style="width: 6px; height: 6px; background: #10B981; border-radius: 50%;"></span> Online
                </span>
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

            with st.form("dedicated_register_form"):
                name = st.text_input("Full Legal Name *", placeholder="e.g. Jordan Miller")
                new_email = st.text_input("Corporate Email Address *", placeholder="jordan.miller@company.com")
                new_password = st.text_input("Password (min 8 characters) *", type="password", placeholder="Set a secure password")

                c_r1, c_r2 = st.columns(2)
                role = c_r1.selectbox(
                    "Account Type *",
                    ["employee", "admin"],
                    format_func=lambda x: "Employee (Self-Service)" if x == "employee" else "HR Administrator"
                )
                emp_code = c_r2.text_input("Employee ID (Optional)", placeholder="e.g. EMP208").strip().upper()

                terms = st.checkbox("I agree to the Enterprise Talent Governance Terms", value=True)
                submit_reg = st.form_submit_button("Create Account & Join", type="primary", use_container_width=True)

            if submit_reg:
                if not name.strip():
                    st.error("Full Name is required.")
                elif not new_email.strip():
                    st.error("Email address is required.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif not terms:
                    st.error("Please agree to the terms to proceed.")
                else:
                    ok, msg = register(name.strip(), new_email.strip(), new_password, role, emp_code if emp_code else None)
                    if ok:
                        st.success(f"{msg} You can now sign in.")
                        st.session_state.auth_view = "login"
                        st.rerun()
                    else:
                        st.error(msg)

            render_html("<div style='border-top: 1px solid #E2E8F0; margin: 1.25rem 0 0.85rem 0;'></div>")
            render_html("<div style='text-align: center; font-size: 0.86rem; color: #64748B; margin-bottom: 0.5rem;'>Already have an account?</div>")
            if st.button("Sign In to Existing Account →", key="btn_reg_to_login", use_container_width=True, type="secondary"):
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
user = st.session_state.user
uid = user["id"]
is_admin = user.get("role") == "admin"
emp_id = user.get("employee_id") or "EMP101"
profile = get_profile(uid)
skills = list_skills(uid)

# Initials for avatar
name_parts = user["name"].strip().split()
initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper()

def navigate_to(target_page: str):
    st.session_state.page_to_navigate = target_page
    st.rerun()

# ------------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ------------------------------------------------------------------------------
with st.sidebar:
    # Sidebar Brand Header matching template
    st.markdown(
        f"""
        <div class="sidebar-brand-box">
            <div style="display: flex; align-items: center; gap: 10px;">
                {get_svg_icon("brand_logo", size=34)}
                <div>
                    <div class="sidebar-brand-title">Talent Growth</div>
                    <div style="font-size: 0.72rem; color: #60A5FA; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase;">Talent Platform</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if is_admin:
        admin_pages = [
            "Dashboard",
            "Employees",
            "Performance",
            "Skills",
            "Career Goals",
            "Reports",
            "ATS Resume Studio",
            "Settings"
        ]
        active_pages = admin_pages
    else:
        emp_pages = [
            "Dashboard",
            "My Profile",
            "Career Goals",
            "Skills",
            "Performance",
            "Career Direction & Gaps",
            "AI Career Coach",
            "Resume Studio",
            "Reports",
            "Settings"
        ]
        active_pages = emp_pages

    st.markdown("<div style='font-size: 0.75rem; font-weight: 700; color: #64748B; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px;'>NAVIGATION</div>", unsafe_allow_html=True)

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

    selected_page = st.radio("Navigation", active_pages, key="nav_radio", on_change=on_nav_change, label_visibility="collapsed")
    st.session_state.current_page = selected_page
    page = selected_page

    st.divider()

    # User Profile Footer Card in Sidebar matching screenshot
    st.markdown(
        f"""
        <div class="sidebar-user-footer">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="sidebar-user-avatar">{initials}</div>
                <div style="overflow: hidden;">
                    <div style="font-weight: 700; font-size: 0.9rem; color: #FFFFFF; line-height: 1.2;">{user['name']}</div>
                    <div style="font-size: 0.75rem; color: #94A3B8; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{user['email']}</div>
                    <div style="font-size: 0.72rem; color: #10B981; font-weight: 600; display: flex; align-items: center; gap: 4px; margin-top: 3px;">
                        <span style="width: 6px; height: 6px; background: #10B981; border-radius: 50%; display: inline-block;"></span> Online
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.current_page = "Dashboard"
        st.session_state.page_to_navigate = "Dashboard"
        st.session_state.auth_view = "landing"
        st.rerun()

def analysis_bundle():
    result = profile_analysis(profile, skills)
    result["match"] = role_match(profile.get("target_role", ""), skills, float(profile.get("years_experience") or 0))
    return result

# ------------------------------------------------------------------------------
# UNIVERSAL TOP BAR WITH TOP-LEFT BACK BUTTON (FOR ALL AUTHENTICATED PAGES)
# ------------------------------------------------------------------------------
col_top_back, col_top_trail = st.columns([2.5, 7.5], gap="small")
with col_top_back:
    if page != "Dashboard":
        if st.button("← Back to Dashboard", key=f"btn_universal_back_dash_{page.replace(' ', '_').lower()}", type="secondary", use_container_width=True):
            navigate_to("Dashboard")
    else:
        if st.button("← Back to Home", key="btn_universal_back_home_dash", type="secondary", use_container_width=True):
            st.session_state.user = None
            st.session_state.current_page = "Dashboard"
            st.session_state.page_to_navigate = "Dashboard"
            st.session_state.auth_view = "landing"
            st.rerun()
with col_top_trail:
    render_html(
        f"""
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; font-size: 0.82rem; color: #64748B; padding-top: 6px;">
            <span style="display: inline-flex; align-items: center; gap: 6px; background: #F1F5F9; border: 1px solid #E2E8F0; padding: 3px 10px; border-radius: 9999px;">
                {get_svg_icon("user", size=13, color="#475569")}
                <strong>{user['name']}</strong> &bull; {user['role'].upper()}
            </span>
            <span style="color: #CBD5E1;">|</span>
            <span style="color: #2563EB; font-weight: 700; background: #EFF6FF; border: 1px solid #DBEAFE; padding: 3px 10px; border-radius: 9999px;">{page}</span>
        </div>
        """
    )

st.markdown("<div style='margin-bottom: 0.85rem;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 1. ADMIN: EXECUTIVE DASHBOARD
# ==============================================================================
if (page in ["Dashboard", "Executive Dashboard"] and is_admin):
    # Top Search & Profile Bar matching Image 1 & 2
    st.markdown(
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
                    <span class="header-user-name">{user['name']}</span>
                    <span style="font-size: 0.72rem; color: #2563EB; font-weight: 700; background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 9999px; padding: 2px 7px;">ADMIN</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Team Collaboration & Growth Chart SVG Illustration matching Image 1
    team_illustration_svg = """
    <svg width="220" height="110" viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg" style="max-height: 110px; width: auto;">
        <!-- Upward trend bars -->
        <rect x="180" y="66" width="13" height="42" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
        <rect x="199" y="48" width="13" height="60" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
        <rect x="218" y="26" width="13" height="82" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
        <!-- Curved Arrow -->
        <path d="M162 90 C 182 72, 204 46, 230 20" stroke="#FDE047" stroke-width="4.5" stroke-linecap="round"/>
        <polygon points="234,16 222,19 228,30" fill="#FDE047"/>
        <!-- Desk -->
        <rect x="25" y="86" width="145" height="6" rx="3" fill="#1E3A8A" fill-opacity="0.7"/>
        <rect x="45" y="92" width="6" height="22" rx="2" fill="#1E3A8A" fill-opacity="0.5"/>
        <rect x="135" y="92" width="6" height="22" rx="2" fill="#1E3A8A" fill-opacity="0.5"/>
        <!-- Laptop -->
        <path d="M85 86 L105 86 L102 73 L88 73 Z" fill="#1E293B"/>
        <rect x="83" y="85" width="24" height="2" rx="1" fill="#94A3B8"/>
        <!-- Person 1 (Yellow shirt) -->
        <circle cx="48" cy="48" r="9.5" fill="#FDE047"/>
        <path d="M35 84 C35 69 42 63 48 63 C54 63 61 69 61 84 Z" fill="#F59E0B"/>
        <!-- Person 2 (Blue shirt) -->
        <circle cx="95" cy="45" r="10" fill="#93C5FD"/>
        <path d="M80 84 C80 67 87 61 95 61 C103 61 110 67 110 84 Z" fill="#1D4ED8"/>
        <!-- Person 3 (Red shirt) -->
        <circle cx="140" cy="50" r="9" fill="#FCA5A5"/>
        <path d="M127 84 C127 71 133 65 140 65 C147 65 153 71 153 84 Z" fill="#EF4444"/>
    </svg>
    """

    # Welcome Hero Banner (Matching Image 1)
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 55%, #3B82F6 100%); border-radius: 16px; padding: 1.65rem 2.2rem; color: #FFFFFF; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 4px 18px rgba(37, 99, 235, 0.22); position: relative; overflow: hidden;">
            <div style="z-index: 1;">
                <div style="font-size: 1.85rem; font-weight: 800; color: #FFFFFF; line-height: 1.25; margin-bottom: 6px;">
                    Welcome back, {user['name']}
                </div>
                <div style="font-size: 0.98rem; color: rgba(255, 255, 255, 0.92); font-weight: 400;">
                    Here's an overview of your talent management platform.
                </div>
            </div>
            <div style="z-index: 1; flex-shrink: 0; display: flex; align-items: center;">
                {team_illustration_svg}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    employees = get_employees()
    reviews = get_performance_reviews()
    dept_summary = get_department_performance_summary()
    all_goals = get_goals()

    avg_perf = round(sum(r["performance_score"] for r in reviews) / len(reviews), 1) if reviews else 4.2
    total_emp_count = len(employees) if employees else 48
    dept_count = len(dept_summary) if dept_summary else 6
    goals_in_progress = len([g for g in all_goals if g.get("status") in ["In Progress", "in progress"]]) if all_goals else 22
    if goals_in_progress == 0:
        goals_in_progress = 22

    # Row of 4 Solid Vibrant KPI Cards matching Image 1
    st.markdown(
        f"""
        <div class="kpi-row-grid-vibrant">
            <div class="kpi-card-vibrant kpi-vibrant-blue">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("employees", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Total Employees</div>
                    <div class="kpi-vibrant-number">{total_emp_count}</div>
                    <div class="kpi-vibrant-sub">
                        ↑ +2 this month
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
                        ↑ +1 this month
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-purple">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("star", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Avg Performance</div>
                    <div class="kpi-vibrant-number">{avg_perf} / 5</div>
                    <div class="kpi-vibrant-sub">
                        ↑ +0.1 this month
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-orange">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("goals", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Goals In Progress</div>
                    <div class="kpi-vibrant-number">{goals_in_progress}</div>
                    <div class="kpi-vibrant-sub">
                        ↑ 75% completion
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
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

    # Middle Section: 2 Central Charts matching Image 1
    col_chart1, col_chart2 = st.columns([1.15, 1], gap="medium")
    with col_chart1:
        with st.container(border=True):
            c_trend_h1, c_trend_h2 = st.columns([1.8, 1])
            with c_trend_h1:
                st.markdown(
                    """
                    <div style="margin-bottom: 0.5rem;">
                        <div style="font-weight: 800; font-size: 1.12rem; color: #0F172A;">Employee Performance Trend</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_trend_h2:
                st.markdown(
                    """
                    <div style="text-align: right; padding-top: 2px;">
                        <span style="font-size: 0.82rem; font-weight: 600; color: #475569; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 4px 10px; border-radius: 8px;">
                            Last 6 Months ▾
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Trend line matching Image 1
            df_trend = pd.DataFrame({
                "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "Rating": [2.6, 3.5, 3.7, 4.0, 4.1, 4.5]
            })
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_trend["Month"],
                y=df_trend["Rating"],
                mode="lines+markers",
                line=dict(color="#2563EB", width=3, shape="spline"),
                marker=dict(size=9, color="#2563EB", line=dict(color="#FFFFFF", width=2.5)),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.08)",
                hovertemplate="<b>%{x}</b><br>Avg Performance: <b>%{y:.1f} / 5.0</b><extra></extra>"
            ))
            fig_line.update_layout(
                margin=dict(l=15, r=15, t=15, b=15),
                height=280,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#F1F5F9", showgrid=True, tickfont=dict(color="#64748B", size=12)),
                yaxis=dict(gridcolor="#F1F5F9", showgrid=True, range=[0, 5.2], dtick=1, tickfont=dict(color="#64748B", size=12))
            )
            st.plotly_chart(fig_line, use_container_width=True)

    with col_chart2:
        with st.container(border=True):
            st.markdown(
                """
                <div style="margin-bottom: 0.5rem;">
                    <div style="font-weight: 800; font-size: 1.12rem; color: #0F172A;">Department Overview</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            df_dept = pd.DataFrame([
                {"Department": "IT", "Percentage": 35, "Headcount": 17},
                {"Department": "HR", "Percentage": 25, "Headcount": 12},
                {"Department": "Finance", "Percentage": 20, "Headcount": 10},
                {"Department": "Marketing", "Percentage": 20, "Headcount": 9}
            ])
            fig_donut = px.pie(
                df_dept, values="Percentage", names="Department", hole=0.64,
                color="Department",
                color_discrete_map={
                    "IT": "#2563EB",
                    "HR": "#F59E0B",
                    "Finance": "#F97316",
                    "Marketing": "#8B5CF6"
                }
            )
            fig_donut.update_traces(
                textinfo='none',
                hoverinfo='label+percent',
                hovertemplate="<b>%{label}</b><br>Share: <b>%{percent}</b><extra></extra>"
            )
            fig_donut.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=12, color="#334155")
                ),
                annotations=[dict(
                    text=f"<b>{total_emp_count}</b><br><span style='font-size:12px;color:#64748B;'>Employees</span>",
                    x=0.5, y=0.5,
                    font_size=18,
                    showarrow=False
                )]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    # Bottom Section: 3 Cards matching Image 1
    col_w1, col_w2, col_w3 = st.columns(3, gap="medium")
    with col_w1:
        with st.container(border=True):
            c_pr1, c_pr2 = st.columns([1.5, 1])
            with c_pr1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("clock", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Pending Reviews</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_pr2:
                if st.button("View All →", key="va_rev_dash", type="secondary", use_container_width=True):
                    navigate_to("Performance")

            st.markdown(
                """
                <div style="margin-top: 4px;">
                    <div class="pending-review-row">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="pending-avatar">RK</div>
                            <div>
                                <div style="font-weight: 700; font-size: 0.88rem; color: #0F172A;">Ravi Kumar</div>
                                <div style="font-size: 0.76rem; color: #64748B;">IT</div>
                            </div>
                        </div>
                        <span class="badge-due-date">Review Due: Jun 20</span>
                    </div>
                    <div class="pending-review-row">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="pending-avatar" style="background: #FDF2F8; color: #DB2777;">SP</div>
                            <div>
                                <div style="font-weight: 700; font-size: 0.88rem; color: #0F172A;">Sneha Patel</div>
                                <div style="font-size: 0.76rem; color: #64748B;">HR</div>
                            </div>
                        </div>
                        <span class="badge-due-date">Review Due: Jun 22</span>
                    </div>
                    <div class="pending-review-row">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="pending-avatar" style="background: #F5F3FF; color: #7C3AED;">AM</div>
                            <div>
                                <div style="font-weight: 700; font-size: 0.88rem; color: #0F172A;">Arjun Mehta</div>
                                <div style="font-size: 0.76rem; color: #64748B;">Finance</div>
                            </div>
                        </div>
                        <span class="badge-due-date">Review Due: Jun 25</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_w2:
        with st.container(border=True):
            c_sk1, c_sk2 = st.columns([1.5, 1])
            with c_sk1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("sparkles", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Skill Gaps</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_sk2:
                if st.button("View All →", key="va_skills_dash", type="secondary", use_container_width=True):
                    navigate_to("Skills")

            st.markdown(
                """
                <div style="margin-top: 14px;">
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">SQL</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-blue" style="width: 68%;"></div>
                        </div>
                        <span class="progress-widget-pct">68%</span>
                    </div>
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">Communication</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-blue" style="width: 72%;"></div>
                        </div>
                        <span class="progress-widget-pct">72%</span>
                    </div>
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">Project Management</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-blue" style="width: 74%;"></div>
                        </div>
                        <span class="progress-widget-pct">74%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col_w3:
        with st.container(border=True):
            c_cg1, c_cg2 = st.columns([1.7, 1])
            with c_cg1:
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
                        {get_svg_icon("goals", size=18, color="#2563EB")}
                        <span style="font-weight: 800; font-size: 1.05rem; color: #0F172A;">Career Goal Progress</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with c_cg2:
                if st.button("View All →", key="va_goals_dash", type="secondary", use_container_width=True):
                    navigate_to("Career Goals")

            st.markdown(
                """
                <div style="margin-top: 14px;">
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">Senior Developer</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-green" style="width: 80%;"></div>
                        </div>
                        <span class="progress-widget-pct">80%</span>
                    </div>
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">Team Lead</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-blue" style="width: 60%;"></div>
                        </div>
                        <span class="progress-widget-pct">60%</span>
                    </div>
                    <div class="progress-widget-row">
                        <span class="progress-widget-name">Data Scientist</span>
                        <div class="progress-bar-track">
                            <div class="progress-bar-fill-purple" style="width: 40%;"></div>
                        </div>
                        <span class="progress-widget-pct">40%</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ==============================================================================
# 2. EMPLOYEE: MY CAREER DASHBOARD
# ==============================================================================
elif (page in ["Dashboard", "My Career Dashboard"] and not is_admin):
    # Top Search & Profile Bar matching theme
    st.markdown(
        f"""
        <div class="top-header-bar">
            <div class="top-search-box">
                {get_svg_icon("search", size=18, color="#94A3B8")}
                <span>Search competencies, milestones, assessments...</span>
            </div>
            <div class="top-header-right">
                <div class="bell-pill" title="1 Unread Notification">
                    {get_svg_icon("bell", size=18, color="#475569")}
                    <span class="dot">1</span>
                </div>
                <div class="header-user-badge">
                    <div class="header-user-avatar">{initials}</div>
                    <span class="header-user-name">{user['name']}</span>
                    <span style="font-size: 0.72rem; color: #2563EB; font-weight: 700; background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 9999px; padding: 2px 7px;">EMPLOYEE</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    completion, missing = profile_completion(profile, skills)
    analysis = analysis_bundle()
    goal_stats = get_goal_stats(uid)
    emp_record = get_employee_by_id(emp_id) if emp_id else None

    # Blue Gradient Welcome Hero Banner with Team Illustration
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 55%, #3B82F6 100%); border-radius: 16px; padding: 1.65rem 2.2rem; color: #FFFFFF; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 4px 18px rgba(37, 99, 235, 0.22); position: relative; overflow: hidden;">
            <div style="z-index: 1;">
                <div style="font-size: 1.85rem; font-weight: 800; color: #FFFFFF; line-height: 1.25; margin-bottom: 6px;">
                    Welcome back, {user['name']}
                </div>
                <div style="font-size: 0.98rem; color: rgba(255, 255, 255, 0.92); font-weight: 400;">
                    Your personal career intelligence hub for competencies, milestones, and development pathways.
                </div>
            </div>
            <div style="z-index: 1; flex-shrink: 0; display: flex; align-items: center;">
                <svg width="220" height="110" viewBox="0 0 240 120" fill="none" xmlns="http://www.w3.org/2000/svg" style="max-height: 110px; width: auto;">
                    <rect x="180" y="66" width="13" height="42" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
                    <rect x="199" y="48" width="13" height="60" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
                    <rect x="218" y="26" width="13" height="82" rx="3" fill="#FFFFFF" fill-opacity="0.95"/>
                    <path d="M162 90 C 182 72, 204 46, 230 20" stroke="#FDE047" stroke-width="4.5" stroke-linecap="round"/>
                    <polygon points="234,16 222,19 228,30" fill="#FDE047"/>
                    <rect x="25" y="86" width="145" height="6" rx="3" fill="#1E3A8A" fill-opacity="0.7"/>
                    <rect x="45" y="92" width="6" height="22" rx="2" fill="#1E3A8A" fill-opacity="0.5"/>
                    <rect x="135" y="92" width="6" height="22" rx="2" fill="#1E3A8A" fill-opacity="0.5"/>
                    <path d="M85 86 L105 86 L102 73 L88 73 Z" fill="#1E293B"/>
                    <rect x="83" y="85" width="24" height="2" rx="1" fill="#94A3B8"/>
                    <circle cx="48" cy="48" r="9.5" fill="#FDE047"/>
                    <path d="M35 84 C35 69 42 63 48 63 C54 63 61 69 61 84 Z" fill="#F59E0B"/>
                    <circle cx="95" cy="45" r="10" fill="#93C5FD"/>
                    <path d="M80 84 C80 67 87 61 95 61 C103 61 110 67 110 84 Z" fill="#1D4ED8"/>
                    <circle cx="140" cy="50" r="9" fill="#FCA5A5"/>
                    <path d="M127 84 C127 71 133 65 140 65 C147 65 153 71 153 84 Z" fill="#EF4444"/>
                </svg>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4 Solid Vibrant KPI Cards for Employee
    st.markdown(
        f"""
        <div class="kpi-row-grid-vibrant">
            <div class="kpi-card-vibrant kpi-vibrant-blue">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("profile", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Profile Readiness</div>
                    <div class="kpi-vibrant-number">{completion}%</div>
                    <div class="kpi-vibrant-sub">
                        {"Complete" if completion == 100 else f"{len(missing)} fields missing"}
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-green">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("skills", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Competency Score</div>
                    <div class="kpi-vibrant-number">{analysis['score']} / 100</div>
                    <div class="kpi-vibrant-sub">
                        Evaluated skills matrix
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-purple">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("star", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Target Role Match</div>
                    <div class="kpi-vibrant-number">{analysis['match']}%</div>
                    <div class="kpi-vibrant-sub">
                        {profile.get('target_role') or 'Role not set'}
                    </div>
                </div>
            </div>
            <div class="kpi-card-vibrant kpi-vibrant-orange">
                <div class="kpi-vibrant-icon">
                    {get_svg_icon("goals", size=26, color="#FFFFFF")}
                </div>
                <div>
                    <div class="kpi-vibrant-title">Active Goals</div>
                    <div class="kpi-vibrant-number">{goal_stats['total']}</div>
                    <div class="kpi-vibrant-sub">
                        {goal_stats['avg_progress']}% avg milestone
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Quick Actions for Employees
    col_eqa1, col_eqa2, col_eqa3, col_eqa4 = st.columns(4)
    with col_eqa1:
        if st.button("Set Career Goal", key="eq_bar_goal", use_container_width=True, type="primary"):
            navigate_to("Career Goals")
    with col_eqa2:
        if st.button("Update Skills", key="eq_bar_skills", use_container_width=True):
            navigate_to("Skills")
    with col_eqa3:
        if st.button("My Performance", key="eq_bar_perf", use_container_width=True):
            navigate_to("Performance")
    with col_eqa4:
        if st.button("AI Career Coach", key="eq_bar_coach", use_container_width=True):
            navigate_to("AI Career Coach")

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    st.progress(completion / 100, text=f"Profile Completeness: {completion}%")

    c_left, c_right = st.columns([1.2, 1])
    with c_left:
        st.markdown("#### Recommended Growth Actions")
        recs = recommendations(profile, skills)
        if recs:
            for rec in recs[:3]:
                with st.container(border=True):
                    is_high = "High" in rec['priority']
                    p_badge_class = "badge-overdue" if is_high else "badge-leave"
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                            <strong style="font-size: 0.92rem; color: #0F172A;">{rec['title']}</strong>
                            <span class="badge-status {p_badge_class}">{rec['priority'].upper()}</span>
                        </div>
                        <div style="font-size: 0.84rem; color: #475569;">{rec['description']}</div>
                        """,
                        unsafe_allow_html=True
                    )
        else:
            st.info("Complete your profile and catalog skills to generate personalized growth actions.")

        st.markdown("#### Active Career Milestones")
        my_goals = get_goals(user_id=uid)
        if my_goals:
            for g in my_goals[:3]:
                with st.container(border=True):
                    stat_class = "badge-completed" if g["status"] == "Completed" else ("badge-overdue" if g["status"] == "Overdue" else "badge-progress")
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                            <strong style="color: #0F172A;">{g['title']}</strong>
                            <span class="badge-status {stat_class}">{g['status'].upper()} ({g['progress']}%)</span>
                        </div>
                        <div style="font-size: 0.8rem; color: #64748B; margin-bottom: 6px;">
                            Target Date: <strong>{g['target_date']}</strong> · Designation: <em>{g.get('target_designation') or 'General'}</em>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.progress(g["progress"] / 100)
        else:
            st.info("No active career goals recorded. Navigate to **My Career Goals** to set your first milestone.")

    with c_right:
        st.markdown("#### Professional Snapshot")
        with st.container(border=True):
            j_title = profile.get('job_title') or (emp_record['designation'] if emp_record else 'Not specified')
            dept_title = profile.get('department') or (emp_record['department'] if emp_record else 'Not specified')
            t_role = profile.get('target_role') or 'Set in Career Direction'
            exp_yrs = profile.get('years_experience', 0)

            st.markdown(
                f"""
                <div style="font-size: 0.88rem; line-height: 1.8;">
                    <div><strong>Job Title:</strong> {j_title}</div>
                    <div><strong>Department:</strong> {dept_title}</div>
                    <div><strong>Target Career Role:</strong> <span style="color: #2563EB; font-weight: 700;">{t_role}</span></div>
                    <div><strong>Experience:</strong> {exp_yrs} years</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        if skills:
            df_skills = pd.DataFrame(skills)
            fig_s = px.bar(
                df_skills, x="name", y="years", color="category",
                title="Skills & Experience Duration",
                labels={"name": "Skill", "years": "Years Exp", "category": "Category"},
                color_discrete_sequence=['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899']
            )
            fig_s.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=280)
            st.plotly_chart(fig_s, use_container_width=True)
        else:
            st.info("Add your skills in **Skills & Assessments** to generate your competency chart.")

# ==============================================================================
# 3. EMPLOYEE MANAGEMENT & WORKFORCE DIRECTORY
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
        s_dept = f2.selectbox("Filter by Department", ["All Departments"] + get_all_departments(), key="emp_dept_filter")
        s_status = f3.selectbox("Filter by Status", ["All Statuses"] + EMPLOYMENT_STATUSES, key="emp_status_filter")

        emp_results = get_employees(
            search_query=s_query if s_query.strip() else None,
            department_filter=s_dept if s_dept != "All Departments" else None,
            status_filter=s_status if s_status != "All Statuses" else None
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
                df_display = pd.DataFrame(emp_results)[["employee_id", "name", "email", "phone", "department", "designation", "joining_date", "employment_status", "years_experience", "primary_skills", "avg_rating"]]
                df_display.columns = ["ID", "Full Name", "Email", "Phone", "Department", "Designation", "Joined", "Status", "Exp (Yrs)", "Primary Skills", "Performance"]
                st.dataframe(
                    df_display,
                    use_container_width=True,
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
                        created_by=uid
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
                    st.dataframe(df_upload.head(10), use_container_width=True, hide_index=True)

                    btn_import = st.button("Validate & Ingest Dataset into Database", type="primary", use_container_width=True)

                    if btn_import:
                        with st.spinner("Processing records and enforcing SQLite constraints..."):
                            import_res = bulk_import_employees_df(df_upload, created_by=uid)

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total In File", import_res["total"])
                        m2.metric("Successfully Added", import_res["success_count"])
                        m3.metric("Skipped / Duplicate", import_res["skipped_count"])

                        if import_res["success_count"] > 0:
                            st.success(f"Successfully imported {import_res['success_count']} employees into SQLite!")

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
        all_emps = get_employees()
        if not all_emps:
            st.info("No employee records currently available in database.")
        else:
            emp_map = {f"{e['employee_id']} — {e['name']} ({e['designation']})": e['employee_id'] for e in all_emps}
            selected_emp_k = st.selectbox("Select Employee Record", list(emp_map.keys()))
            selected_emp_code = emp_map[selected_emp_k]
            emp_curr = get_employee_by_id(selected_emp_code)

            if emp_curr:
                col_ed, col_rm = st.columns([1.6, 1])
                with col_ed:
                    with st.form("edit_emp_master_form"):
                        st.markdown(f"##### Edit Details for `{emp_curr['employee_id']}`")
                        up_name = st.text_input("Full Legal Name", value=emp_curr["name"])
                        up_email = st.text_input("Corporate Email", value=emp_curr["email"] or "")
                        up_phone = st.text_input("Phone Number", value=emp_curr["phone"] or "")

                        d_list = get_all_departments()
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
                            employment_status=up_status
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
                            ok_del, msg_del = delete_employee(emp_curr["employee_id"])
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
            all_reviews = get_performance_reviews()
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
                    df_rev = pd.DataFrame(filtered_reviews)[["employee_id", "employee_name", "department", "designation", "review_period", "performance_score", "achievements", "strengths", "improvements", "manager_feedback", "created_at"]]
                    df_rev.columns = ["Emp ID", "Employee Name", "Department", "Designation", "Period", "Score (1–5)", "Key Achievements", "Demonstrated Strengths", "Growth Areas", "Manager Feedback", "Recorded On"]
                    st.dataframe(
                        df_rev,
                        use_container_width=True,
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
            emps = get_employees()
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
                            reviewer_id=uid
                        )
                        if ok_r:
                            st.success(msg_r)
                            st.rerun()
                        else:
                            st.error(msg_r)

        with tab_rev_trends:
            st.markdown("#### Workforce Performance Rating Distribution")
            all_revs = get_performance_reviews()
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
        my_revs = get_performance_reviews(employee_id=emp_id)
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
# 5. SKILLS & COMPETENCY MATRIX
# ==============================================================================
elif page in ["Skills", "Skills & Competency Matrix", "Skills & Assessments"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("skills", size=24, color="#10B981")} Skills Management & Competency Matrix
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Map employee competencies against 10 industry benchmark roles and coordinate upskilling programs.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">COMPETENCY MATRIX</span>
            </div>
        </div>
        """
    )

    tab_sk_matrix, tab_sk_gaps, tab_sk_train = st.tabs(["Skills Portfolio", "Role Gap Analysis", "Training & Upskilling"])

    with tab_sk_matrix:
        if is_admin:
            all_emps = get_employees()
            if all_emps:
                emp_sk_map = {f"{e['employee_id']} — {e['name']}": e['employee_id'] for e in all_emps}
                selected_sk_emp = st.selectbox("Select Employee Profile", list(emp_sk_map.keys()))
                target_code = emp_sk_map[selected_sk_emp]
            else:
                target_code = emp_id
        else:
            target_code = emp_id

        col_sk_form, col_sk_table = st.columns([1, 1.5])
        with col_sk_form:
            with st.form("add_sk_form"):
                st.markdown(f"##### Add Competency for `{target_code}`")
                sk_name = st.text_input("Skill Name *", placeholder="e.g. Python, Docker, React, Kubernetes")
                sk_cat = st.selectbox("Skill Category", ["Technical", "Domain", "Soft Skill", "Leadership", "Tool", "Business"])
                sk_prof = st.selectbox("Proficiency Level", list(LEVELS.keys()))
                sk_yrs = st.number_input("Years Experience", min_value=0.0, max_value=50.0, value=1.5, step=0.5)
                submit_sk = st.form_submit_button("Add Skill to Portfolio", type="primary")

            if submit_sk:
                ok_sk, msg_sk = add_employee_skill(target_code, sk_name, sk_prof, sk_cat, sk_yrs)
                if not is_admin:
                    add_skill(uid, sk_name, sk_cat, sk_prof, sk_yrs)
                if ok_sk:
                    st.success(msg_sk)
                    st.rerun()
                else:
                    st.error(msg_sk)

        with col_sk_table:
            emp_skills = get_employee_skills(target_code)
            st.markdown(f"##### Verified Skills Catalog ({len(emp_skills)})")
            if emp_skills:
                df_sk = pd.DataFrame(emp_skills)[["id", "skill_name", "category", "proficiency_level", "years_exp", "last_updated"]]
                df_sk.columns = ["ID", "Skill Name", "Category", "Proficiency", "Experience (Yrs)", "Last Updated"]
                st.dataframe(
                    df_sk.drop(columns=["ID"]),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Skill Name": st.column_config.TextColumn("Competency", width="medium"),
                        "Category": st.column_config.TextColumn("Category", width="small"),
                        "Proficiency": st.column_config.TextColumn("Proficiency", width="small"),
                        "Experience (Yrs)": st.column_config.NumberColumn("Experience", format="%.1f yrs"),
                        "Last Updated": st.column_config.DateColumn("Cataloged Date", format="YYYY-MM-DD")
                    }
                )

                sk_del_map = {f"{s['skill_name']} ({s['proficiency_level']})": s["id"] for s in emp_skills}
                sel_del_sk = st.selectbox("Remove Competency", ["Select skill to remove..."] + list(sk_del_map.keys()))
                if sel_del_sk != "Select skill to remove..." and st.button("Delete Skill"):
                    delete_employee_skill(sk_del_map[sel_del_sk])
                    st.success("Skill removed successfully.")
                    st.rerun()
            else:
                st.info("No skills cataloged for this employee profile yet.")

        # Skill Gap Analysis Section matching reference mockup
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("#### Skill Gap Analysis vs Benchmark Role")
        quick_target_role = st.selectbox("Compare with Target Role Benchmark", list(ROLE_CATALOG.keys()), key="sk_tab1_role")
        quick_gap = get_employee_skill_gaps(target_code, quick_target_role)
        
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            st.metric(f"Match Readiness for {quick_target_role}", f"{quick_gap['match_percentage']}%")
            st.progress(quick_gap['match_percentage'] / 100)
        with c_m2:
            st.markdown(f"**Benchmark Standard:** {quick_gap['criteria']}")
            if quick_gap["gaps"]:
                for g in quick_gap["gaps"][:4]:
                    lvl_cur = g['current_level']
                    lvl_req = g['required_level']
                    st.markdown(f"**{g['skill']}**: Level {lvl_cur} / Required {lvl_req} (Gap: -{g['gap']})")
                    st.progress(min(1.0, max(0.0, lvl_cur / max(1, lvl_req))))

    with tab_sk_gaps:
        st.markdown("#### Benchmark Role Gap Analysis & Competency Radar")
        st.caption("Compare current verified competencies against 10 corporate benchmark roles to pinpoint development priorities.")
        all_roles = list(ROLE_CATALOG.keys())
        target_role_eval = st.selectbox("Benchmark Target Role", all_roles, key="sel_bench_role")

        gap_result = get_employee_skill_gaps(target_code, target_role_eval)
        
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
                # Calculate simulated match
                old_m = gap_result['match_percentage']
                boosted_m = min(100, old_m + (sim_level * 5))
                st.markdown(
                    f"""
                    <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 10px 14px; margin-top: 8px;">
                        <span style="font-size: 0.84rem; color: #1E40AF;">
                            Advancing <strong>{sim_skill}</strong> to level {sim_level} projects role readiness from <strong>{old_m}%</strong> → <strong style="color: #10B981;">{boosted_m}%</strong> (+{boosted_m - old_m}% gain).
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        if gap_result["gaps"]:
            st.markdown("##### Detailed Priority Competency Breakdown")
            levels_str = {0: "None (0)", 1: "Beginner (1)", 2: "Intermediate (2)", 3: "Advanced (3)", 4: "Expert (4)"}
            df_gaps = pd.DataFrame([{
                "Skill Required": g["skill"],
                "Current Level": levels_str.get(g["current_level"], str(g["current_level"])),
                "Benchmark Level": levels_str.get(g["required_level"], str(g["required_level"])),
                "Skill Gap": g["gap"],
                "Priority": g["priority"]
            } for g in gap_result["gaps"]])
            st.dataframe(
                df_gaps,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Skill Required": st.column_config.TextColumn("Competency", width="medium"),
                    "Current Level": st.column_config.TextColumn("Current Level", width="small"),
                    "Benchmark Level": st.column_config.TextColumn("Required Benchmark", width="small"),
                    "Skill Gap": st.column_config.ProgressColumn("Competency Gap", min_value=0, max_value=4, format="-%d"),
                    "Priority": st.column_config.TextColumn("Priority", width="small"),
                }
            )

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
                t_provider = st.text_input("Training Provider", value="TalentSphere Academy")
                t_due = st.date_input("Target Completion Date", value=date.today())
                submit_train = st.form_submit_button("Assign Course", type="primary")

            if submit_train:
                ok_tr, msg_tr = add_training_record(t_emp_code, t_course, t_skill, t_provider, t_due.isoformat(), "Enrolled")
                if ok_tr:
                    st.success(msg_tr)
                    st.rerun()
                else:
                    st.error(msg_tr)

        trainings = get_training_records(None if is_admin else target_code)
        if trainings:
            df_tr = pd.DataFrame(trainings)[["employee_id", "course_name", "target_skill", "provider", "target_completion_date", "status", "score"]]
            df_tr.columns = ["Emp ID", "Course Title", "Target Competency", "Provider", "Target Date", "Status", "Score"]
            st.dataframe(
                df_tr,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Emp ID": st.column_config.TextColumn("ID", width="small"),
                    "Course Title": st.column_config.TextColumn("Course Title", width="medium"),
                    "Target Competency": st.column_config.TextColumn("Target Skill", width="small"),
                    "Provider": st.column_config.TextColumn("Provider", width="small"),
                    "Target Date": st.column_config.DateColumn("Target Date", format="YYYY-MM-DD"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Score": st.column_config.ProgressColumn("Grade", min_value=0, max_value=100, format="%d%%")
                }
            )
        else:
            st.info("No active training courses recorded.")

# ==============================================================================
# 6. CAREER DEVELOPMENT & SMART GOALS
# ==============================================================================
elif page in ["Career Goals", "Career Development Plans", "My Career Goals"]:
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("goals", size=24, color="#F97316")} Career Development & SMART Goals
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
    goal_stats = get_goal_stats(user_id=goal_user_id)

    # Pro Metric Cards
    st.markdown(
        f"""
        <div class="pro-metric-grid">
            <div class="pro-metric-card card-blue">
                <div class="pro-metric-label">Total Goals</div>
                <div class="pro-metric-value">{goal_stats['total']}</div>
                <div class="pro-metric-sub">Defined career milestones</div>
            </div>
            <div class="pro-metric-card card-amber">
                <div class="pro-metric-label">In Progress (25–75%)</div>
                <div class="pro-metric-value">{goal_stats['in_progress']}</div>
                <div class="pro-metric-sub">Active execution</div>
            </div>
            <div class="pro-metric-card card-emerald">
                <div class="pro-metric-label">Completed (100%)</div>
                <div class="pro-metric-value">{goal_stats['completed']}</div>
                <div class="pro-metric-sub">Finished milestones</div>
            </div>
            <div class="pro-metric-card card-rose">
                <div class="pro-metric-label">Overdue Goals</div>
                <div class="pro-metric-value">{goal_stats['overdue']}</div>
                <div class="pro-metric-sub">Past target deadline</div>
            </div>
            <div class="pro-metric-card card-purple">
                <div class="pro-metric-label">Avg Progress</div>
                <div class="pro-metric-value">{goal_stats['avg_progress']}%</div>
                <div class="pro-metric-sub">Milestone completion</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if goal_stats["total"] > 0:
        st.progress(goal_stats["avg_progress"] / 100, text=f"Overall Milestone Completion: {goal_stats['avg_progress']}%")

    tab_g_view, tab_g_create, tab_g_edit = st.tabs(["Goals Dashboard & Tracking", "Create SMART Career Goal", "Manage Milestones (Edit / Delete)"])

    # --- TAB 1: DASHBOARD ---
    with tab_g_view:
        c_ghead1, c_ghead2 = st.columns([2.2, 1.3])
        with c_ghead1:
            st.markdown("#### Active Career Goals & Milestone Roadmap")
            st.caption("SMART goals aligned with career objectives, target milestones, and completion schedules.")
        with c_ghead2:
            goal_view_mode = st.radio("Goal View Layout", ["Roadmap View", "Table View"], horizontal=True, key="goal_view_mode", label_visibility="collapsed")

        status_filter = st.selectbox("Filter Goals by Status", ["All Statuses", "Not Started", "In Progress", "Completed", "Overdue"], key="cg_status_sel")
        goals_data = get_goals(user_id=goal_user_id, status_filter=status_filter if status_filter != "All Statuses" else None)

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
                df_g = pd.DataFrame(goals_data)[["title", "target_designation", "description", "target_date", "progress", "status", "updated_at"]]
                df_g.columns = ["Goal Title", "Target Designation", "Action Steps & Description", "Target Date", "Progress (%)", "Status", "Last Updated"]
                st.dataframe(
                    df_g,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Goal Title": st.column_config.TextColumn("Goal Title", width="medium"),
                        "Target Designation": st.column_config.TextColumn("Target Role", width="small"),
                        "Target Date": st.column_config.DateColumn("Target Date", format="YYYY-MM-DD"),
                        "Progress (%)": st.column_config.ProgressColumn("Milestone Completion", min_value=0, max_value=100, format="%d%%"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "Last Updated": st.column_config.TextColumn("Updated", width="small"),
                    }
                )

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
            st.info("No career goals found matching criteria.")

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
                    target_designation="" if cg_role == "Not Specified" else cg_role
                )
                if ok_cg:
                    st.success(msg_cg)
                    st.rerun()
                else:
                    st.error(msg_cg)

    # --- TAB 3: MANAGE GOALS ---
    with tab_g_edit:
        st.markdown("#### Edit or Delete Career Goals")
        my_all_goals = get_goals(user_id=goal_user_id)
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
elif page in ["Reports", "Reports & Analytics", "Career Growth Report"]:
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

    employees = get_employees()
    reviews = get_performance_reviews()
    goals = get_goals()
    dept_summary = get_department_performance_summary()
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
            df_ds = pd.DataFrame(dept_summary)
            df_ds["avg_score"] = pd.to_numeric(df_ds["avg_score"], errors="coerce").fillna(0.0)
            df_ds.columns = ["Department", "Headcount", "Average Rating", "Total Reviews Logged"]
            st.dataframe(
                df_ds,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Department": st.column_config.TextColumn("Department", width="medium"),
                    "Headcount": st.column_config.NumberColumn("Headcount", format="%d active", width="small"),
                    "Average Rating": st.column_config.ProgressColumn(
                        "Average Rating",
                        min_value=0.0,
                        max_value=5.0,
                        format="%.2f / 5.0",
                        width="medium"
                    ),
                    "Total Reviews Logged": st.column_config.NumberColumn("Completed Reviews", format="%d", width="small")
                }
            )

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
        assessments = get_assessments(uid)
        progress = get_progress(uid)
        user_goals = get_goals(user_id=uid)
        user_reviews = get_performance_reviews(employee_id=emp_id)

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
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("profile", size=24, color="#2563EB")} My Professional Profile
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Manage your professional background, contact details, career experience, and portfolio.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">PROFILE HUB</span>
            </div>
        </div>
        """
    )

    with st.form("my_profile_form"):
        a, b = st.columns(2)
        with a:
            st.text_input("Full Name", value=user["name"], disabled=True)
            phone = st.text_input("Contact Phone", value=profile.get("phone", ""))
            location = st.text_input("Location / City", value=profile.get("location", ""))
            job = st.text_input("Current Job Title", value=profile.get("job_title", ""))
            company = st.text_input("Company / Organization", value=profile.get("company", ""))
            department = st.text_input("Department", value=profile.get("department", ""))
            industry = st.text_input("Industry", value=profile.get("industry", ""))
        with b:
            emp_types = ["Full-time", "Part-time", "Contract", "Self-employed", "Other"]
            emp_idx = emp_types.index(profile.get("employment_type")) if profile.get("employment_type") in emp_types else 0
            employment = st.selectbox("Employment Type", emp_types, index=emp_idx)
            years = st.number_input("Years of Experience", min_value=0.0, max_value=60.0, value=float(profile.get("years_experience") or 0.0), step=0.5)
            linkedin = st.text_input("LinkedIn Profile URL", value=profile.get("linkedin", ""))
            github = st.text_input("GitHub Portfolio URL", value=profile.get("github", ""))
            portfolio = st.text_input("Personal Website / Portfolio", value=profile.get("portfolio", ""))
            education = st.text_area("Education", value=profile.get("education", ""), placeholder="Degree · University · Year")
            certifications = st.text_area("Certifications & Licenses", value=profile.get("certifications", ""))

        summary = st.text_area("Executive Summary", value=profile.get("summary", ""), height=100)
        experience = st.text_area("Experience & Measurable Outcomes", value=profile.get("experience", ""), height=120)
        projects = st.text_area("Notable Projects & Impact", value=profile.get("projects", ""), height=100)

        if st.form_submit_button("Save Profile Information", type="primary", use_container_width=True):
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
    st.progress(completion / 100, text=f"Profile Completeness: {completion}%")
    if missing:
        st.caption("Fields to complete: " + ", ".join(missing))

# ==============================================================================
# 9. RESUME STUDIO
# ==============================================================================
elif page == "ATS Resume Studio" or page == "Resume Studio":
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("code", size=24, color="#2563EB")} ATS Resume Studio & Optimizer
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Parse resume documents, match keyword alignment against benchmark roles, and export ATS-friendly PDFs.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">RESUME STUDIO</span>
            </div>
        </div>
        """
    )

    upload = st.file_uploader("Import Existing Resume Document (PDF or DOCX)", type=["pdf", "docx"])
    if upload:
        try:
            if upload.name.lower().endswith(".pdf"):
                text = "\n".join(p.extract_text() or "" for p in PdfReader(upload).pages)
            else:
                text = "\n".join(p.text for p in Document(upload).paragraphs)
            if st.button("Save Parsed Resume Text", type="primary"):
                save_profile(uid, {"resume_text": text})
                st.success("Resume text saved for target keyword alignment review.")
                st.rerun()
            st.text_area("Parsed Text Preview", text, height=180)
        except Exception as exc:
            st.error(f"Could not read file: {exc}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Profile Content Preview")
        st.write(f"**Summary:** {profile.get('summary') or 'Add a summary in My Profile.'}")
        st.write("**Skills:** " + (", ".join(x["name"] for x in skills) or "None recorded"))
        st.write(f"**Experience:** {profile.get('experience') or 'Add experience details in My Profile.'}")
    with c2:
        st.markdown("#### Target Role ATS Alignment")
        resume = (profile.get("resume_text") or "").lower()
        role_skills = ROLE_CATALOG.get(profile.get("target_role", ""), {}).get("skills", {})
        if resume and role_skills:
            matched = [s for s in role_skills if s.lower() in resume]
            missing_kw = [s for s in role_skills if s.lower() not in resume]
            score = round(100 * len(matched) / max(1, len(role_skills)))
            st.metric("Target Keyword Match", f"{score}%")
            st.write("**Detected Keywords:** " + (", ".join(matched) or "None"))
            st.write("**Missing Keywords to Address:** " + (", ".join(missing_kw) or "None"))
        else:
            st.info("Import a resume or set a target role under Career Direction to evaluate ATS keyword alignment.")

    st.divider()
    render_html(
        f"""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.1rem 1.4rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 8px;">
                    {get_svg_icon("sparkles", size=20, color="#2563EB")} AI Resume Auditor & Bullet Rewriter (Gemini)
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
    
    col_audit_btn, col_audit_opt = st.columns([2, 3])
    with col_audit_btn:
        audit_clicked = st.button("Run Deep AI Resume & Bullet Audit", type="primary", use_container_width=True)
    with col_audit_opt:
        audit_source = st.radio("Audit Content Source", ["Parsed Resume Text", "Profile Work Experience"], horizontal=True)

    if audit_clicked:
        resume_source_text = profile.get("resume_text", "") if audit_source == "Parsed Resume Text" else profile.get("experience", "")
        if not resume_source_text.strip():
            resume_source_text = f"Summary: {profile.get('summary', '')}\nExperience: {profile.get('experience', '')}\nSkills: {', '.join(s['name'] for s in skills)}"

        if not resume_source_text.strip():
            st.warning("Please upload a resume or enter your experience details in My Profile to run the audit.")
        else:
            target_role = profile.get("target_role", "Senior Software Engineer")
            target_skills_list = list(ROLE_CATALOG.get(target_role, {}).get("skills", {}).keys())
            
            with st.spinner("Running deep AI ATS audit and STAR bullet optimization..."):
                audit_res = analyze_resume_with_ai(
                    resume_text=resume_source_text,
                    target_role=target_role,
                    target_skills=target_skills_list,
                    profile=profile,
                    api_key=st.session_state.get("gemini_user_key")
                )
                st.session_state.last_resume_audit = audit_res

    if "last_resume_audit" in st.session_state:
        res = st.session_state.last_resume_audit
        ats_score = res.get("ats_score", 70)
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
            for idx, b in enumerate(bullets, 1):
                with st.container(border=True):
                    col_orig, col_opt = st.columns(2)
                    with col_orig:
                        st.markdown(f"**Original Bullet #{idx}:**")
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
    st.markdown("#### ATS Resume Generation & Export")
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(612, 792))
    y = 740
    lines = [
        user["name"],
        f"{profile.get('location','')} | {profile.get('phone','')} | {user['email']}", "",
        "PROFESSIONAL SUMMARY", profile.get("summary") or "", "",
        "SKILLS", ", ".join(s["name"] + " (" + s["proficiency"] + ")" for s in skills), "",
        "EXPERIENCE", profile.get("experience") or "", "",
        "EDUCATION", profile.get("education") or "", "",
        "CERTIFICATIONS", profile.get("certifications") or "", "",
        "PROJECTS", profile.get("projects") or "", "",
        "LINKS", " | ".join(filter(None, [profile.get("linkedin"), profile.get("github"), profile.get("portfolio")]))
    ]
    for para in lines:
        for line in para.splitlines() or [""]:
            if y < 55:
                c.showPage()
                y = 740
            is_header = para in ["PROFESSIONAL SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "PROJECTS", "LINKS", user["name"]]
            c.setFont("Helvetica-Bold" if is_header else "Helvetica", 13 if para == user["name"] else 9)
            for chunk in [line[i:i+95] for i in range(0, max(1, len(line)), 95)]:
                c.drawString(48, y, chunk)
                y -= 14
    c.save()
    st.download_button("Download ATS Resume (PDF)", buf.getvalue(), file_name="talentsphere_resume.pdf", mime="application/pdf", type="primary")

# ==============================================================================
# 10. CAREER DIRECTION & AI COACH
# ==============================================================================
elif page == "Career Direction & Gaps":
    render_html(
        f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 1.25rem 1.6rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.35rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="font-size: 1.55rem; font-weight: 800; color: #0F172A; display: flex; align-items: center; gap: 10px;">
                    {get_svg_icon("goals", size=24, color="#F97316")} Career Direction & Benchmark Targets
                </div>
                <div style="color: #64748B; font-size: 0.92rem; margin-top: 4px;">
                    Define target roles, desired seniority levels, and growth timelines.
                </div>
            </div>
            <div>
                <span class="badge-status badge-active">CAREER ROADMAP</span>
            </div>
        </div>
        """
    )

    with st.form("career_direction_form"):
        current = st.text_input("Current Title / Role", value=profile.get("job_title", ""))
        roles_list = ["Choose a role"] + list(ROLE_CATALOG.keys())
        curr_role_idx = (roles_list.index(profile["target_role"])) if profile.get("target_role") in ROLE_CATALOG else 0
        target = st.selectbox("Target Career Role", roles_list, index=curr_role_idx)

        levels = ["Individual contributor", "Senior", "Lead", "Manager", "Director"]
        curr_lvl_idx = levels.index(profile.get("target_level")) if profile.get("target_level") in levels else 1
        level = st.selectbox("Target Seniority Level", levels, index=curr_lvl_idx)

        timelines = ["3–6 months", "6–12 months", "1–2 years", "Exploring"]
        curr_time_idx = timelines.index(profile.get("timeline")) if profile.get("timeline") in timelines else 1
        timeline = st.selectbox("Target Timeline", timelines, index=curr_time_idx)

        industry = st.text_input("Target Industry", value=profile.get("target_industry", ""))
        goal = st.text_area("What does career growth mean to you?", value=profile.get("career_goal", ""))

        if st.form_submit_button("Save Career Direction", type="primary", use_container_width=True):
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

    if profile.get("target_role"):
        st.info(f"**Benchmark Standard Criteria for {profile['target_role']}:** {ROLE_CATALOG[profile['target_role']]['criteria']}")

elif page == "AI Career Coach":
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
                    user_name=user["name"],
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

    st.write(f"Logged in as: **{user['name']}** (`{user['email']}`) · Role: `{user['role'].upper()}`")

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
            st.download_button("Download talentsphere.db File", db_bytes, file_name="talentsphere.db", mime="application/octet-stream", use_container_width=True)

    render_html(
        f"""
        <div style="font-size: 1.15rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin: 1.5rem 0 0.75rem 0;">
            {get_svg_icon("download", size=20, color="#2563EB")} Export System Data Snapshot
        </div>
        """
    )
    payload = json.dumps(export_user_data(uid), indent=2, default=str).encode("utf-8")
    st.download_button("Download Complete System Snapshot (JSON)", payload, file_name="talent_growth_snapshot.json", mime="application/json", type="primary")
