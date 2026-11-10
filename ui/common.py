from __future__ import annotations

import html

import streamlit as st

from config import PAGE_ANALYZER, PAGE_BUILDER

def render_page_header(eyebrow: str, title: str, subtitle: str, pills: list[str]) -> None:
    pill_markup = "".join(
        f'<span class="hero-pill">{html.escape(pill)}</span>' for pill in pills
    )
    st.markdown(
        f"""
        <section class="hero">
            <div class="eyebrow">{html.escape(eyebrow)}</div>
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
            <div class="hero-pills">{pill_markup}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="brand-row">
                    <div class="brand-mark">◈</div>
                    <div>
                        <div class="brand-title">Resume Intelligence</div>
                        <div class="brand-subtitle">ATS Ecosystem</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
        page = st.radio(
            "Workspace",
            [PAGE_BUILDER, PAGE_ANALYZER],
            label_visibility="collapsed",
        )
        st.markdown(
            """
            <div class="sidebar-note">
                <strong>Private by design.</strong><br>
                Resume content is processed in memory for this session only. Nothing is stored on disk or shared with third parties beyond the AI request you initiate.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="footer-note">Deterministic ATS scoring · 100-point model</div>',
            unsafe_allow_html=True,
        )
    return page
