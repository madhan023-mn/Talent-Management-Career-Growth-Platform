from __future__ import annotations
import os
import base64
from pathlib import Path
from typing import Any
import streamlit as st

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent
CSS_PATH = BASE_DIR / "assets" / "style.css"

def get_css() -> str:
    """Reads and returns the custom CSS string from assets/style.css."""
    if CSS_PATH.is_file():
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def load_css(custom_path: Path | str | None = None) -> None:
    """Injects custom CSS into the Streamlit application."""
    if custom_path:
        p = Path(custom_path)
        css = p.read_text(encoding="utf-8") if p.is_file() else ""
    else:
        css = get_css()

    if css:
        st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)

# Aliases for convenience
apply_css = load_css
inject_css = load_css

def apply_saas_chart_theme(fig: Any, height: int | None = None, title: str | None = None, show_legend: bool = True) -> Any:
    """Applies a clean, modern Enterprise SaaS Plotly visual theme."""
    if fig is None:
        return fig
    layout_update: dict[str, Any] = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            "color": "#475569",
            "size": 12,
        },
        "colorway": [
            "#2563EB", "#10B981", "#8B5CF6", "#F59E0B",
            "#06B6D4", "#EC4899", "#3B82F6", "#14B8A6"
        ],
        "margin": dict(l=15, r=15, t=40 if title else 20, b=20),
    }
    if height:
        layout_update["height"] = height
    if title:
        layout_update["title"] = {
            "text": title,
            "font": {"size": 14, "color": "#0F172A", "family": "'Inter', sans-serif"},
            "x": 0.02,
            "y": 0.98,
        }
    if not show_legend:
        layout_update["showlegend"] = False

    try:
        fig.update_layout(**layout_update)
        fig.update_xaxes(
            gridcolor="#F1F5F9",
            zerolinecolor="#E2E8F0",
            tickfont={"size": 11, "color": "#64748B"},
            showline=False,
        )
        fig.update_yaxes(
            gridcolor="#F1F5F9",
            zerolinecolor="#E2E8F0",
            tickfont={"size": 11, "color": "#64748B"},
            showline=False,
        )
    except Exception:
        pass
    return fig

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
    "building": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "profile": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "lock": '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "sliders": '<line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="1" x2="7" y1="14" y2="14"/><line x1="9" x2="15" y1="8" y2="8"/><line x1="17" x2="23" y1="16" y2="16"/>',
    "palette": '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.563-2.512 5.563-5.563C22 6.5 17.5 2 12 2Z"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
}

@st.cache_data
def _build_svg_data_uri_util(inner_svg: str, width: int, height: int, stroke_color: str, fill_color: str) -> str:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_svg}</svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")

def get_svg_icon(name: str, size: int = 18, color: str = "#4F46E5", extra_style: str = "") -> str:
    """Returns an inline, standalone, crisp SVG vector icon as a data URI img."""
    inner = _SVG_RAW_PATHS.get(name)
    if not inner:
        return f'<span style="display:inline-block; width:{size}px; height:{size}px; {extra_style}"></span>'

    stroke_color = color if (color and color != "currentColor") else "#334155"
    fill_color = stroke_color if name == "star" else "none"
    uri = _build_svg_data_uri_util(inner, size, size, stroke_color, fill_color)
    return f'<img src="{uri}" width="{size}" height="{size}" style="display: inline-block; vertical-align: middle; border: none; {extra_style}" alt="{name}" />'

