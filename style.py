from __future__ import annotations
import os
from pathlib import Path
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
