"""Shared Streamlit helpers: page setup, sidebar, badges."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.data.data_loader import load_astronauts
from src.utils.constants import ENVIRONMENTS, LEVEL_NAMES

ROOT = Path(__file__).resolve().parents[2]


def page(title: str, icon: str = "🚀") -> tuple[dict, str]:
    """Call first in every page. Returns (astronaut, environment_key)."""
    st.set_page_config(page_title=f"{title} · Vital Space", page_icon=icon, layout="wide")
    css = ROOT / "assets" / "styles.css"
    if css.exists():
        st.markdown(f"<style>{css.read_text()}</style>", unsafe_allow_html=True)
    logo = ROOT / "assets" / "logo.png"
    if logo.exists():
        st.logo(str(logo))
    crew = load_astronauts()
    with st.sidebar:
        st.markdown("**Crew member**")
        names = {c["id"]: f'{c["name"]} · {c["role"]}' for c in crew}
        aid = st.selectbox("Crew member", list(names), format_func=names.get, key="astronaut_id", label_visibility="collapsed")
        st.markdown("**Environment**")
        env = st.radio("Environment", list(ENVIRONMENTS), format_func=lambda k: ENVIRONMENTS[k]["name"],
                       key="environment", label_visibility="collapsed")
        st.caption(ENVIRONMENTS[env]["delay"])
        st.divider()
        st.caption("Reference ranges are general adult values for demonstration, not medical advice.")
    return next(c for c in crew if c["id"] == aid), env


def badge(level: int, text: str | None = None) -> str:
    return f'<span class="vs-badge vs-l{level}">{text or LEVEL_NAMES[level]}</span>'


def banner(level: int, title: str, text: str) -> None:
    st.markdown(
        f'<div class="vs-banner vs-l{level}">{badge(level)}<div><strong>{title}</strong><br>{text}</div></div>',
        unsafe_allow_html=True,
    )
