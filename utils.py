from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

import streamlit as st

from ats_data import SKILL_GROUPS
from models import ResumeContent

def get_secret(name: str) -> str | None:
    try:
        value = st.secrets[name]
        return str(value) if value else None
    except Exception:
        return None


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def clean_generated_text(value: Any) -> str:
    text = clean_line(str(value or ""))
    text = re.sub(r"^[\-*•\u2022]+\s*", "", text)
    text = text.replace("**", "").replace("__", "")
    return text.strip()


def slugify_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", (name or "").strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("_")
    return cleaned or "resume"


def safe_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if not re.match(r"^https?://", candidate, re.I):
        candidate = "https://" + candidate
    try:
        parsed = urlparse(candidate)
    except Exception:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    if any(char in candidate for char in ['"', "'", "<", ">"]):
        return ""
    return candidate


def display_url(value: str) -> str:
    return re.sub(r"^https?://(?:www\.)?", "", (value or "").strip(), flags=re.I).rstrip("/")


def split_skills(raw: str) -> list[str]:
    parts = re.split(r"[,;\n|•]+", raw or "")
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        skill = clean_line(part)
        if not skill:
            continue
        key = skill.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(skill[:60])
        if len(result) >= 40:
            break
    return result


def _skill_matches(skill: str, keyword: str) -> bool:
    skill_lower = skill.casefold()
    keyword_lower = keyword.casefold()
    if len(keyword_lower) <= 2:
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(keyword_lower)}(?![a-z0-9])",
                skill_lower,
            )
        )
    return keyword_lower in skill_lower


def categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    unassigned: list[str] = []
    for skill in skills:
        assigned = False
        for category, keywords in SKILL_GROUPS.items():
            if any(_skill_matches(skill, keyword) for keyword in keywords):
                categories.setdefault(category, []).append(skill)
                assigned = True
                break
        if not assigned:
            unassigned.append(skill)
    if unassigned:
        categories["Additional Skills"] = unassigned
    return categories


def build_local_content(
    title: str,
    experience_notes: str,
    raw_skills: str,
) -> ResumeContent:
    skills = split_skills(raw_skills)
    focus = clean_line(title) or "Professional"
    skill_phrase = ", ".join(skills[:5]) if skills else "cross-functional initiatives"
    summary = (
        f"{focus} focused on translating requirements into reliable, high-quality outcomes. "
        f"Brings practical exposure to {skill_phrase} and a structured, detail-oriented approach to problem solving. "
        "Known for clear communication, ownership, and delivering measurable value through continuous improvement."
    )
    bullets: list[str] = []
    for line in (experience_notes or "").splitlines():
        candidate = clean_line(re.sub(r"^[\-*•\u2022\d.)\s]+", "", line))
        if candidate and candidate not in bullets:
            bullets.append(candidate[:500])
        if len(bullets) >= 8:
            break
    if not bullets and experience_notes.strip():
        for sentence in re.split(r"(?<=[.!?])\s+", clean_line(experience_notes)):
            if sentence:
                bullets.append(sentence[:500])
            if len(bullets) >= 8:
                break
    return {
        "summary": summary,
        "experience_bullets": bullets,
        "skills": categorize_skills(skills),
    }
