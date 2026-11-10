from __future__ import annotations

import html

import streamlit as st

from config import EMAIL_RE, MODEL_OPTIONS
from models import Profile, ResumeContent
from services.ai_service import generate_ai_resume, resolve_api_key, resolve_default_model
from services.pdf_service import build_pdf_resume
from ui.common import render_page_header
from utils import (
    build_local_content,
    clean_generated_text,
    clean_line,
    display_url,
    safe_url,
    slugify_filename,
    split_skills,
)

def render_resume_preview(
    profile: Profile,
    content: ResumeContent,
    mode: str,
) -> None:
    full_name = clean_line(profile.get("full_name", ""))
    professional_title = clean_line(profile.get("professional_title", ""))
    email = clean_line(profile.get("email", ""))
    phone = clean_line(profile.get("phone", ""))
    location = clean_line(profile.get("city_state", ""))
    linkedin = clean_line(profile.get("linkedin", ""))
    github = clean_line(profile.get("github", ""))

    if full_name:
        name_html = html.escape(full_name)
    else:
        name_html = '<span style="color:#94A3B8;">Your Name</span>'

    contact_items: list[str] = []
    if email and EMAIL_RE.fullmatch(email):
        contact_items.append(
            f'<a href="mailto:{html.escape(email, quote=True)}">{html.escape(email)}</a>'
        )
    elif email:
        contact_items.append(html.escape(email))
    if phone:
        contact_items.append(html.escape(phone))
    if location:
        contact_items.append(html.escape(location))
    if linkedin:
        linkedin_url = safe_url(linkedin)
        label = html.escape(display_url(linkedin) or "LinkedIn")
        if linkedin_url:
            contact_items.append(
                f'<a href="{html.escape(linkedin_url, quote=True)}" target="_blank" rel="noopener noreferrer">LinkedIn · {label}</a>'
            )
        else:
            contact_items.append(label)
    if github:
        github_url = safe_url(github)
        label = html.escape(display_url(github) or "GitHub / Portfolio")
        if github_url:
            contact_items.append(
                f'<a href="{html.escape(github_url, quote=True)}" target="_blank" rel="noopener noreferrer">GitHub · {label}</a>'
            )
        else:
            contact_items.append(label)

    separator = '<span class="contact-sep">|</span>'
    contact_html = separator.join(contact_items)

    summary = clean_line(str(content.get("summary", "")))
    summary_html = (
        f'<p class="resume-summary">{html.escape(summary)}</p>'
        if summary
        else '<p class="empty-note">Add your profile details to build the summary.</p>'
    )

    bullets = [
        clean_generated_text(item)
        for item in content.get("experience_bullets", [])
        if clean_generated_text(item)
    ]
    if bullets:
        bullets_html = "<ul>" + "".join(
            f"<li>{html.escape(bullet)}</li>" for bullet in bullets[:8]
        ) + "</ul>"
    else:
        bullets_html = (
            '<p class="empty-note">Add rough experience or project notes, then generate your resume.</p>'
        )

    education_lines = [
        clean_line(line)
        for line in str(profile.get("education", "")).splitlines()
        if clean_line(line)
    ]
    education_html = (
        '<div class="resume-section"><h2>Education &amp; Certifications</h2>'
        + "".join(f"<p class=\"resume-summary\">{html.escape(line)}</p>" for line in education_lines)
        + "</div>"
        if education_lines
        else ""
    )

    skills = content.get("skills", {})
    skill_rows: list[str] = []
    if isinstance(skills, dict):
        for category, items in list(skills.items())[:7]:
            if not isinstance(items, list):
                continue
            clean_items = [clean_line(str(item)) for item in items if clean_line(str(item))]
            if not clean_items:
                continue
            skill_rows.append(
                '<div class="skill-row">'
                f"<strong>{html.escape(clean_line(str(category)))}:</strong> "
                f"{html.escape(' • '.join(clean_items))}"
                "</div>"
            )
    skills_html = (
        "".join(skill_rows)
        if skill_rows
        else '<p class="empty-note">Add comma-separated skills to populate this section.</p>'
    )

    title_html = (
        f'<div class="resume-title">{html.escape(professional_title)}</div>'
        if professional_title
        else ""
    )
    contact_block = (
        f'<div class="resume-contact">{contact_html}</div>'
        if contact_items
        else '<div class="resume-contact"><span class="empty-note">Email · Phone · Location · LinkedIn · Portfolio</span></div>'
    )

    mode_label = "AI-generated draft" if mode == "ai" else "Live draft preview"
    st.markdown(
        f"""
        <div class="preview-toolbar">
            <div class="preview-title">Resume Preview</div>
            <div class="mode-badge">{html.escape(mode_label)}</div>
        </div>
        <article class="resume-paper">
            <h1>{name_html}</h1>
            {title_html}
            {contact_block}
            <div class="resume-section">
                <h2>Executive Summary</h2>
                {summary_html}
            </div>
            <div class="resume-section">
                <h2>Experience &amp; Projects</h2>
                {bullets_html}
            </div>
            {education_html}
            <div class="resume-section">
                <h2>Skills</h2>
                {skills_html}
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def validate_builder_inputs(profile: Profile, notes: str, skills: str) -> list[str]:
    errors: list[str] = []
    if not profile["full_name"].strip():
        errors.append("Full Name is required.")
    if not profile["professional_title"].strip():
        errors.append("Professional Title is required.")
    email = profile["email"].strip()
    if not email:
        errors.append("Email Address is required.")
    elif not EMAIL_RE.fullmatch(email):
        errors.append("Enter a valid email address.")
    if not notes.strip() and not skills.strip():
        errors.append("Add work experience notes, project notes, or skills before generating.")
    return errors


def render_builder() -> None:
    render_page_header(
        "Feature 01",
        "AI Resume Builder",
        "Transform rough career notes into a polished, ATS-ready resume. Generate structured content with AI, review the live preview, and export a clean single-column PDF.",
        ["Gemini-powered", "ATS-safe layout", "Instant PDF export"],
    )

    left, right = st.columns([1.02, 0.98], gap="large")

    with left:
        st.markdown(
            """
            <div class="panel-heading">
                <h3>Profile &amp; Career Details</h3>
                <span>Step 1 · Input</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("⚙️ AI engine & API settings", expanded=False):
            api_key_entry = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="AIza...",
                help="Leave blank to use the GEMINI_API_KEY environment variable or Streamlit secret.",
                key="gemini_key_input",
            )
            default_model = resolve_default_model()
            model = st.selectbox(
                "Model",
                MODEL_OPTIONS,
                index=MODEL_OPTIONS.index(default_model),
                help="Gemini 2.5 Flash is the fast default. Gemini 2.5 Pro is available for deeper writing.",
            )
            effective_key = resolve_api_key(api_key_entry)
            if effective_key:
                st.caption("Gemini API key detected. The key is used only for your generation request.")
            else:
                st.caption("No Gemini API key detected. Set GEMINI_API_KEY before generating.")

        full_name = st.text_input(
            "Full Name *",
            placeholder="Aarav Sharma",
            max_chars=80,
        )
        professional_title = st.text_input(
            "Professional Title *",
            placeholder="Senior Software Engineer",
            max_chars=120,
        )
        email_col, phone_col = st.columns(2)
        with email_col:
            email = st.text_input(
                "Email Address *",
                placeholder="aarav@example.com",
                max_chars=120,
            )
        with phone_col:
            phone = st.text_input(
                "Phone Number",
                placeholder="+91 98765 43210",
                max_chars=40,
            )
        location_col, linkedin_col = st.columns(2)
        with location_col:
            city_state = st.text_input(
                "City / State",
                placeholder="Bengaluru, Karnataka",
                max_chars=100,
            )
        with linkedin_col:
            linkedin = st.text_input(
                "LinkedIn Profile URL",
                placeholder="linkedin.com/in/aaravsharma",
                max_chars=300,
            )
        github = st.text_input(
            "GitHub / Portfolio URL",
            placeholder="github.com/aaravsharma",
            max_chars=300,
        )
        experience_notes = st.text_area(
            "Work Experience & Projects *",
            height=220,
            placeholder=(
                "Paste rough notes, achievements, or project details. Example:\n"
                "- built payments API used by 3 teams\n"
                "- reduced deployment time by around 40 percent\n"
                "- led migration from monolith to microservices"
            ),
            max_chars=6000,
            help="Rough notes are fine. AI will turn them into action-verb-led bullets without inventing facts.",
        )
        education_notes = st.text_area(
            "Education & Certifications (optional)",
            height=95,
            placeholder="B.Tech in Computer Science, XYZ University, 2022\nAWS Certified Solutions Architect",
            max_chars=1500,
            help="This section is exported exactly as entered so you control the facts.",
        )
        skills_raw = st.text_area(
            "Core Technical Skills & Tools *",
            height=110,
            placeholder="Python, FastAPI, React, PostgreSQL, Docker, AWS, Kubernetes, Git",
            max_chars=1800,
            help="Use commas, semicolons, or new lines to separate skills.",
        )

        generate_clicked = st.button(
            "✨ Generate Professional AI Resume Content",
            type="primary",
            use_container_width=True,
        )
        st.caption(
            "Metric placeholders such as [X%] and [#] must be replaced with accurate numbers before you send the resume."
        )

    profile: Profile = {
        "full_name": clean_line(full_name),
        "professional_title": clean_line(professional_title),
        "email": clean_line(email),
        "phone": clean_line(phone),
        "city_state": clean_line(city_state),
        "linkedin": clean_line(linkedin),
        "github": clean_line(github),
        "education": (education_notes or "").strip(),
    }
    provided_skills = split_skills(skills_raw)

    if generate_clicked:
        validation_errors = validate_builder_inputs(profile, experience_notes, skills_raw)
        if validation_errors:
            with left:
                st.error("Please fix the following before generating:\n\n" + "\n".join(f"- {item}" for item in validation_errors))
        elif not effective_key:
            with left:
                st.error(
                    "Gemini API key is missing. Add it in AI engine settings, set GEMINI_API_KEY, or add it to .streamlit/secrets.toml."
                )
        else:
            with left:
                with st.spinner("Writing your professional resume content..."):
                    try:
                        generated = generate_ai_resume(
                            effective_key,
                            model,
                            profile,
                            experience_notes,
                            provided_skills,
                        )
                        st.session_state["resume_content"] = generated
                        st.session_state["resume_content_mode"] = "ai"
                        st.success(
                            "Professional content generated. Review the preview and replace metric placeholders before downloading."
                        )
                    except Exception as exc:
                        fallback = build_local_content(
                            profile["professional_title"],
                            experience_notes,
                            skills_raw,
                        )
                        st.session_state["resume_content"] = fallback
                        st.session_state["resume_content_mode"] = "fallback"
                        message = clean_line(str(exc))[:400]
                        st.error(
                            f"AI generation failed: {message}. A local draft was created instead; review it carefully before downloading."
                        )

    content = st.session_state.get("resume_content")
    mode = st.session_state.get("resume_content_mode", "draft")
    if not content:
        content = build_local_content(
            profile["professional_title"],
            experience_notes,
            skills_raw,
        )
        mode = "draft"

    with right:
        st.markdown(
            """
            <div class="panel-heading">
                <h3>Live Preview &amp; Export</h3>
                <span>Step 2 · Output</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_resume_preview(profile, content, mode)

        can_download = bool(profile["full_name"]) and bool(
            content.get("experience_bullets") or content.get("skills")
        )
        if can_download:
            try:
                pdf_bytes = build_pdf_resume(profile, content)
                st.download_button(
                    "⬇️ Download ATS-Optimized PDF Resume",
                    data=pdf_bytes,
                    file_name=f"{slugify_filename(profile['full_name'])}_resume.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.markdown(
                    '<p class="pdf-note">Single-column, text-based, and ATS-scannable. No images, icons, or complex tables in the resume body.</p>',
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                st.error(f"PDF generation failed: {clean_line(str(exc))[:300]}")
        else:
            st.button(
                "⬇️ Download ATS-Optimized PDF Resume",
                disabled=True,
                use_container_width=True,
            )
            st.caption("Add your name and some resume content to enable PDF export.")
