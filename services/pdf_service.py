from __future__ import annotations

import html
import io
import os
import re
import unicodedata
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import Profile, ResumeContent
from utils import clean_generated_text, clean_line, display_url, safe_url

PDF_FONT_REGULAR = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"
PDF_FONT_UNICODE = False


def configure_pdf_fonts() -> None:
    global PDF_FONT_REGULAR, PDF_FONT_BOLD, PDF_FONT_UNICODE
    if PDF_FONT_UNICODE:
        return
    candidates = [
        (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ),
        (
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ),
    ]
    for regular_path, bold_path in candidates:
        if not (os.path.exists(regular_path) and os.path.exists(bold_path)):
            continue
        try:
            pdfmetrics.registerFont(TTFont("ResumeSans", regular_path))
            pdfmetrics.registerFont(TTFont("ResumeSans-Bold", bold_path))
        except Exception:
            continue
        PDF_FONT_REGULAR = "ResumeSans"
        PDF_FONT_BOLD = "ResumeSans-Bold"
        PDF_FONT_UNICODE = True
        return


def pdf_safe_text(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    replacements = {
        "₹": "INR ",
        "€": "EUR ",
        "£": "GBP ",
        "•": "-",
        "–": "-",
        "—": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "…": "...",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = "".join(
        char
        for char in text
        if char == " " or unicodedata.category(char)[0] != "C"
    )
    text = re.sub(r"\s+", " ", text).strip()
    if not PDF_FONT_UNICODE:
        text = text.encode("cp1252", "replace").decode("cp1252")
    return html.escape(text, quote=False)


def pdf_url_link(url: str, label: str) -> str:
    safe = safe_url(url)
    escaped_label = pdf_safe_text(label)
    if not safe:
        return escaped_label
    escaped_url = html.escape(safe, quote=True)
    return f'<link href="{escaped_url}" color="#1D4ED8">{escaped_label}</link>'


def build_pdf_resume(profile: Profile, content: ResumeContent) -> bytes:
    configure_pdf_fonts()
    buffer = io.BytesIO()
    full_name = clean_line(profile.get("full_name", "")) or "Resume"
    professional_title = clean_line(profile.get("professional_title", ""))
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"{full_name} - Resume",
        author=full_name,
        subject=professional_title or "Professional Resume",
    )

    name_style = ParagraphStyle(
        "ResumeName",
        fontName=PDF_FONT_BOLD,
        fontSize=20,
        leading=23,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )
    title_style = ParagraphStyle(
        "ResumeTitle",
        fontName=PDF_FONT_BOLD,
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1D4ED8"),
        spaceAfter=5,
    )
    contact_style = ParagraphStyle(
        "ResumeContact",
        fontName=PDF_FONT_REGULAR,
        fontSize=8.4,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#334155"),
    )
    section_style = ParagraphStyle(
        "ResumeSection",
        fontName=PDF_FONT_BOLD,
        fontSize=9.2,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=7,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ResumeBody",
        fontName=PDF_FONT_REGULAR,
        fontSize=9.1,
        leading=12.7,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=body_style,
        fontSize=9.1,
        leading=12.6,
        leftIndent=13,
        firstLineIndent=-9,
        bulletIndent=1,
        spaceAfter=4,
    )

    story: list[Any] = []
    story.append(Paragraph(pdf_safe_text(full_name), name_style))
    if professional_title:
        story.append(Paragraph(pdf_safe_text(professional_title), title_style))

    contact_parts: list[str] = []
    email = clean_line(profile.get("email", ""))
    phone = clean_line(profile.get("phone", ""))
    location = clean_line(profile.get("city_state", ""))
    linkedin = safe_url(profile.get("linkedin", ""))
    github = safe_url(profile.get("github", ""))

    if email:
        contact_parts.append(pdf_safe_text(email))
    if phone:
        contact_parts.append(pdf_safe_text(phone))
    if location:
        contact_parts.append(pdf_safe_text(location))
    if linkedin:
        contact_parts.append(pdf_url_link(linkedin, display_url(linkedin)))
    if github:
        contact_parts.append(pdf_url_link(github, display_url(github)))

    if contact_parts:
        contact_markup = '<font color="#94A3B8"> | </font>'.join(contact_parts)
        contact_table = Table(
            [[Paragraph(contact_markup, contact_style)]],
            colWidths=[document.width],
        )
        contact_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.HexColor("#2563EB")),
                ]
            )
        )
        story.append(contact_table)
    else:
        story.append(Spacer(1, 4))

    def add_section_heading(label: str) -> None:
        heading_table = Table(
            [[Paragraph(pdf_safe_text(label.upper()), section_style)]],
            colWidths=[document.width],
        )
        heading_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.8, colors.HexColor("#1D4ED8")),
                ]
            )
        )
        story.append(heading_table)
        story.append(Spacer(1, 4))

    summary = clean_line(str(content.get("summary", "")))
    if summary:
        add_section_heading("Executive Summary")
        story.append(Paragraph(pdf_safe_text(summary), body_style))

    bullets = [
        clean_generated_text(item)
        for item in content.get("experience_bullets", [])
        if clean_generated_text(item)
    ]
    if bullets:
        add_section_heading("Experience & Projects")
        for bullet in bullets[:8]:
            story.append(
                Paragraph(
                    pdf_safe_text(bullet),
                    bullet_style,
                    bulletText="-",
                )
            )

    education_lines = [
        clean_line(line)
        for line in str(profile.get("education", "")).splitlines()
        if clean_line(line)
    ]
    if education_lines:
        add_section_heading("Education & Certifications")
        for line in education_lines[:6]:
            story.append(Paragraph(pdf_safe_text(line), body_style))

    skill_groups = content.get("skills", {})
    if isinstance(skill_groups, dict) and any(skill_groups.values()):
        add_section_heading("Skills")
        for category, items in list(skill_groups.items())[:7]:
            if not isinstance(items, list):
                continue
            clean_items = [pdf_safe_text(item) for item in items if clean_line(str(item))]
            if not clean_items:
                continue
            row = (
                f"<b>{pdf_safe_text(category)}:</b> "
                + " | ".join(clean_items)
            )
            story.append(Paragraph(row, body_style))

    document.build(story)
    return buffer.getvalue()
