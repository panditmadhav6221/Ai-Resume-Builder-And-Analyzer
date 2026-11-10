from __future__ import annotations

from pathlib import Path

import streamlit as st

STYLES_PATH = Path(__file__).with_name("styles.css")


def inject_theme() -> None:
    styles = STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)
