from __future__ import annotations

import re

APP_TITLE = "AI Resume Builder & Deterministic ATS Analyzer"
PAGE_BUILDER = "📄 AI Resume Builder"
PAGE_ANALYZER = "📊 ATS Score Analyzer"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
MODEL_OPTIONS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-pro",
]
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 150_000
MAX_PDF_PAGES = 40

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,3}\d{2,4}(?!\d)"
)
LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_%.\-]+", re.I
)
GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.\-]+", re.I
)
PORTFOLIO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:behance\.net|dribbble\.com)/[^\s]+", re.I
)
METRIC_RE = re.compile(
    r"(?<![\w.])(?:[₹$€£]\s*)?\d[\d,]*(?:\.\d+)?\s*(?:%|\+|x|k|m|bn|million|billion|crore|lakh)?(?![\w])",
    re.I,
)
