from __future__ import annotations

import streamlit as st

from config import APP_TITLE, PAGE_BUILDER
from ui.analyzer_page import render_analyzer
from ui.builder_page import render_builder
from ui.common import render_sidebar
from ui.theme import inject_theme


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    page = render_sidebar()
    if page == PAGE_BUILDER:
        render_builder()
    else:
        render_analyzer()


if __name__ == "__main__":
    main()
