from __future__ import annotations

import hashlib
import html
from typing import Any

import streamlit as st

from config import MAX_UPLOAD_BYTES
from services.ats_engine import run_ats_audit
from services.resume_parser import extract_resume_text
from ui.common import render_page_header
from utils import clean_line

def render_score_dashboard(result: dict[str, Any]) -> None:
    overall = int(result["overall"])
    status = html.escape(str(result["status"]))
    color = result["color"]
    status_class = {
        "Excellent": "status-excellent",
        "Moderate": "status-moderate",
        "Low": "status-low",
    }.get(result["status"], "status-moderate")
    keyword_score = int(result["keyword"]["points"])
    structure_score = int(result["structure"]["points"])
    impact_score = int(result["impact"]["points"])

    st.markdown(
        f"""
        <div class="score-hero">
            <div class="score-ring" style="--score:{overall};--ring:{color};">
                <div class="score-value">
                    <strong>{overall}%</strong>
                    <span>ATS Score</span>
                </div>
            </div>
            <div class="score-copy">
                <div class="score-kicker">Deterministic Audit Result</div>
                <h2>{status} job alignment</h2>
                <p>The score combines hard keyword coverage, ATS structure, and impact language. It is a diagnostic signal, not a guarantee of any employer's ATS behavior.</p>
                <div class="status-badge {status_class}"><i></i>{status}</div>
            </div>
        </div>
        <div class="subscore-grid">
            <div class="subscore-card">
                <div class="subscore-label"><span>Keyword alignment</span><strong>{keyword_score}/40</strong></div>
                <div class="subscore-bar"><span style="width:{(keyword_score / 40) * 100:.1f}%"></span></div>
            </div>
            <div class="subscore-card">
                <div class="subscore-label"><span>ATS structure</span><strong>{structure_score}/30</strong></div>
                <div class="subscore-bar"><span style="width:{(structure_score / 30) * 100:.1f}%"></span></div>
            </div>
            <div class="subscore-card">
                <div class="subscore-label"><span>Impact language</span><strong>{impact_score}/30</strong></div>
                <div class="subscore-bar"><span style="width:{(impact_score / 30) * 100:.1f}%"></span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chips(items: list[dict[str, Any]], style: str) -> None:
    chips = "".join(
        f'<span class="chip {style}">{html.escape(str(item["display"]))}</span>'
        for item in items
    )
    st.markdown(f'<div class="chip-wrap">{chips}</div>', unsafe_allow_html=True)


def render_ats_results(result: dict[str, Any], file_name: str) -> None:
    st.markdown(
        f"""
        <div class="audit-meta">
            <span class="meta-pill">File · {html.escape(file_name)}</span>
            <span class="meta-pill">Resume words · {result['word_count']:,}</span>
            <span class="meta-pill">Analyzed · {html.escape(result['created_at'])}</span>
            <span class="meta-pill">100-point deterministic model</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_score_dashboard(result)

    st.markdown(
        '<div class="result-heading"><h3>✅ Passed Checks</h3></div>',
        unsafe_allow_html=True,
    )
    st.success(
        "**Layout and content strengths detected**\n\n"
        + "\n".join(f"- {item}" for item in result["passed"])
    )

    st.markdown(
        '<div class="result-heading"><h3>🧩 Keyword Alignment</h3></div>',
        unsafe_allow_html=True,
    )
    missing = result["keyword"]["missing"]
    partial = result["keyword"]["partial"]
    matched = result["keyword"]["matched"]

    if missing:
        st.error(
            f"**Critical keyword gaps · {len(missing)} target term(s) absent from the resume**\n\n"
            "These terms appear in the job description but were not found in the parsed resume text."
        )
        render_chips(missing, "chip-danger")
    elif result["keyword"]["total_terms"]:
        st.success("No critical keyword gaps were detected among the extracted JD terms.")

    if partial:
        st.warning(
            f"**Partial keyword coverage · {len(partial)} term(s) need exact phrasing**\n\n"
            "The concept appears in the resume, but the exact JD phrasing is missing."
        )
        render_chips(partial, "chip-warning")

    if matched:
        st.markdown(
            f"**{len(matched)} directly aligned keyword(s)**",
        )
        render_chips(matched, "chip-success")

    if not result["keyword"]["total_terms"]:
        st.warning(
            "No recognized role-specific keywords were found in the job description. Paste a more detailed JD for a stronger audit."
        )

    structural_gaps: list[str] = []
    if result["structure"]["missing_sections"]:
        structural_gaps.append(
            "Missing section headers: "
            + ", ".join(result["structure"]["missing_sections"])
        )
    if not result["structure"]["linkedin_found"]:
        structural_gaps.append("LinkedIn URL in linkedin.com/in/ format is missing")
    if not result["structure"]["portfolio_found"]:
        structural_gaps.append("GitHub or portfolio URL is missing")
    if structural_gaps:
        st.warning(
            "**Structure and link gaps**\n\n"
            + "\n".join(f"- {item}" for item in structural_gaps)
        )

    st.markdown(
        '<div class="result-heading"><h3>🚀 Actionable Recommendations</h3></div>',
        unsafe_allow_html=True,
    )
    recommendation_html = "".join(
        f'<div class="recommendation"><span class="rec-index">{index}</span><p>{html.escape(item)}</p></div>'
        for index, item in enumerate(result["recommendations"], start=1)
    )
    st.markdown(recommendation_html, unsafe_allow_html=True)

    st.markdown(
        '<div class="footer-note">This audit is deterministic and based only on the text extracted from the uploaded file. ATS platforms vary; use the result as a focused improvement guide.</div>',
        unsafe_allow_html=True,
    )


def render_analyzer() -> None:
    render_page_header(
        "Feature 02",
        "ATS Score Analyzer",
        "Audit any PDF or DOCX resume against a target job description. Get a transparent 100-point score, exact keyword gaps, structure checks, and a prioritized action plan.",
        ["PDF + DOCX parsing", "Exact & partial matching", "No black-box scoring"],
    )

    with st.container(border=True):
        upload_col, jd_col = st.columns([0.92, 1.08], gap="large")
        with upload_col:
            st.markdown(
                '<div class="panel-heading"><h3>Resume File</h3><span>PDF / DOCX</span></div>',
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                "Drag and drop your resume",
                type=["pdf", "docx"],
                help="Maximum file size: 8 MB. Scanned image-only PDFs are not supported.",
                label_visibility="visible",
            )
            if uploaded_file is not None:
                size_mb = uploaded_file.size / (1024 * 1024)
                st.caption(f"{uploaded_file.name} · {size_mb:.2f} MB")
            st.markdown(
                '<div class="workspace-note">Resume text is extracted locally in memory. Only the parsed text and the job description are used for scoring.</div>',
                unsafe_allow_html=True,
            )
        with jd_col:
            st.markdown(
                '<div class="panel-heading"><h3>Target Job Description</h3><span>Paste JD</span></div>',
                unsafe_allow_html=True,
            )
            jd_text = st.text_area(
                "Job description *",
                height=265,
                placeholder=(
                    "Paste the full target JD here. Include responsibilities, required tools, technologies, and preferred qualifications for the most accurate keyword audit."
                ),
                max_chars=30000,
                label_visibility="visible",
            )
        audit_clicked = st.button(
            "🔍 Run ATS Compatibility Audit",
            type="primary",
            use_container_width=True,
        )

    current_hash = None
    if uploaded_file is not None:
        try:
            current_hash = hashlib.sha256(
                uploaded_file.getvalue() + (jd_text or "").encode("utf-8", errors="ignore")
            ).hexdigest()
        except Exception:
            current_hash = None

    if audit_clicked:
        if uploaded_file is None:
            st.error("Upload a PDF or DOCX resume before running the audit.")
        elif not jd_text.strip():
            st.error("Paste the target job description before running the audit.")
        elif len(jd_text.strip()) < 30:
            st.error("The job description is too short for a meaningful audit. Paste the full JD.")
        elif uploaded_file.size > MAX_UPLOAD_BYTES:
            st.error("The uploaded file exceeds the 8 MB limit.")
        else:
            with st.spinner("Parsing resume and running deterministic ATS checks..."):
                try:
                    resume_text, parse_warnings = extract_resume_text(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                    )
                    audit_result = run_ats_audit(resume_text, jd_text)
                    st.session_state["ats_result"] = audit_result
                    st.session_state["ats_file_name"] = uploaded_file.name
                    st.session_state["ats_input_hash"] = current_hash
                    st.session_state["ats_parse_warnings"] = parse_warnings
                except Exception as exc:
                    st.error(f"Could not analyze this resume: {clean_line(str(exc))[:500]}")

    stored_result = st.session_state.get("ats_result")
    if stored_result:
        warnings = st.session_state.get("ats_parse_warnings", [])
        if warnings:
            for warning in warnings:
                st.warning(warning)
        stored_hash = st.session_state.get("ats_input_hash")
        if current_hash and stored_hash and current_hash != stored_hash:
            st.info(
                "The uploaded file or job description has changed since the last audit. Re-run the audit to refresh these results."
            )
        st.divider()
        render_ats_results(
            stored_result,
            st.session_state.get("ats_file_name", "resume"),
        )
