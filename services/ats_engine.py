from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any

from ats_data import ACTION_VERBS, SECTION_PATTERNS, SKILL_GROUPS
from config import EMAIL_RE, GITHUB_RE, LINKEDIN_RE, METRIC_RE, PHONE_RE, PORTFOLIO_RE
from models import AuditResult, ImpactAnalysis, JDTerm, KeywordAnalysis, StructureAnalysis
from utils import clean_line, normalize_text

def count_occurrences(text: str, keyword: str) -> int:
    pattern = re.compile(
        rf"(?<![a-z0-9_]){re.escape(keyword.casefold())}(?![a-z0-9_])",
        re.I,
    )
    return len(pattern.findall(text))


def _stem(word: str) -> str:
    result = word.casefold()
    for suffix in (
        "ational",
        "ization",
        "ations",
        "ation",
        "ments",
        "ment",
        "ingly",
        "edly",
        "ions",
        "ion",
        "ing",
        "ies",
        "ied",
        "ed",
        "es",
        "s",
    ):
        if len(result) - len(suffix) >= 3 and result.endswith(suffix):
            result = result[: -len(suffix)]
            break
    return result[:8]


def _stems_match(first: str, second: str) -> bool:
    if first == second:
        return True
    if min(len(first), len(second)) >= 4:
        return first.startswith(second) or second.startswith(first)
    return False


def _component_words(term: str) -> list[str]:
    return [
        part.casefold()
        for part in re.split(r"[\s/&.+\-]+", term)
        if len(part) >= 2 and part.casefold() not in {"and", "or", "the", "of"}
    ]


def has_loose_term(text: str, term: str) -> bool:
    if count_occurrences(text, term) > 0:
        return True
    components = _component_words(term)
    if len(components) > 1:
        return all(has_loose_term(text, component) for component in components)
    if len(term) <= 2:
        return False
    tokens = re.findall(r"[a-z0-9]+", text)
    needle = _stem(term)
    return any(_stems_match(_stem(token), needle) for token in tokens)


def extract_jd_keywords(jd_text: str) -> list[JDTerm]:
    jd_normalized = normalize_text(jd_text)
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category, terms in SKILL_GROUPS.items():
        for display in terms:
            term = display.casefold()
            if term in seen:
                continue
            frequency = count_occurrences(jd_normalized, term)
            if frequency <= 0:
                continue
            seen.add(term)
            found.append(
                {
                    "term": term,
                    "display": display,
                    "jd_freq": frequency,
                    "word_count": len(term.split()),
                    "category": category,
                }
            )
    found.sort(
        key=lambda item: (
            -item["jd_freq"],
            -item["word_count"],
            item["display"].casefold(),
        )
    )
    return found[:30]


def analyze_keywords(resume_text: str, jd_text: str) -> KeywordAnalysis:
    jd_normalized = normalize_text(jd_text)
    resume_normalized = normalize_text(resume_text)
    terms = extract_jd_keywords(jd_text)

    if not terms:
        return {
            "points": 0,
            "coverage": 0.0,
            "terms": [],
            "matched": [],
            "partial": [],
            "missing": [],
            "detail": [],
            "total_terms": 0,
        }

    selected = terms
    total_weight = 0.0
    weighted_score = 0.0
    matched: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    detail: list[dict[str, Any]] = []

    for item in selected:
        term = item["term"]
        jd_freq = item["jd_freq"]
        exact_freq = count_occurrences(resume_normalized, term)
        weight = (
            1.0
            + min(math.log1p(jd_freq), 2.0)
            + 0.15 * min(max(item["word_count"] - 1, 0), 2)
        )
        if exact_freq > 0:
            frequency_ratio = min(exact_freq / max(jd_freq, 1), 1.0)
            quality = 0.78 + 0.22 * frequency_ratio
            status = "matched"
        elif has_loose_term(resume_normalized, term):
            quality = 0.58
            status = "partial"
        else:
            quality = 0.0
            status = "missing"

        total_weight += weight
        weighted_score += weight * quality
        record = {
            "display": item["display"],
            "category": item["category"],
            "jd_freq": jd_freq,
            "resume_freq": exact_freq,
            "status": status,
            "quality": quality,
        }
        detail.append(record)
        if status == "matched":
            matched.append(record)
        elif status == "partial":
            partial.append(record)
        else:
            missing.append(record)

    coverage = weighted_score / total_weight if total_weight else 0.0
    points = int(round(40 * coverage))
    return {
        "points": max(0, min(points, 40)),
        "coverage": coverage,
        "terms": [item["display"] for item in selected],
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "detail": detail,
        "total_terms": len(selected),
    }


def detect_sections(resume_text: str) -> dict[str, bool]:
    flags = {name: False for name in SECTION_PATTERNS}
    for raw_line in (resume_text or "").splitlines():
        line = raw_line.strip()
        line = re.sub(r"^[\s\-*•\u2022#|]+", "", line)
        line = re.sub(r"^[\d]+[.)]\s*", "", line)
        line = re.sub(r"[\s:|]+$", "", line)
        line = clean_line(line)
        if not line or len(line) > 72 or len(line.split()) > 8:
            continue
        for section, pattern in SECTION_PATTERNS.items():
            if pattern.fullmatch(line):
                flags[section] = True
    return flags


def find_phone(text: str) -> bool:
    for match in PHONE_RE.finditer(text or ""):
        digits = re.sub(r"\D", "", match.group(0))
        if 7 <= len(digits) <= 15:
            return True
    return False


def analyze_structure(resume_text: str) -> StructureAnalysis:
    flags = detect_sections(resume_text)
    email_found = bool(EMAIL_RE.search(resume_text or ""))
    phone_found = find_phone(resume_text or "")
    contact_details = email_found and phone_found
    linkedin_found = bool(LINKEDIN_RE.search(resume_text or ""))
    github_found = bool(GITHUB_RE.search(resume_text or ""))
    portfolio_found = github_found or bool(PORTFOLIO_RE.search(resume_text or ""))

    required_status = {
        "Experience": flags["Experience"],
        "Education": flags["Education"],
        "Skills": flags["Skills"],
        "Projects": flags["Projects"],
        "Contact Info": flags["Contact Info"] or contact_details,
    }
    header_points = sum(4 for found in required_status.values() if found)
    link_points = (5 if linkedin_found else 0) + (5 if portfolio_found else 0)
    points = header_points + link_points

    found_sections = [section for section, found in required_status.items() if found]
    missing_sections = [section for section, found in required_status.items() if not found]

    return {
        "points": max(0, min(points, 30)),
        "headers": required_status,
        "email_found": email_found,
        "phone_found": phone_found,
        "linkedin_found": linkedin_found,
        "github_found": github_found,
        "portfolio_found": portfolio_found,
        "found_sections": found_sections,
        "missing_sections": missing_sections,
        "header_points": header_points,
        "link_points": link_points,
    }


def extract_metrics(resume_text: str) -> list[str]:
    cleaned = EMAIL_RE.sub(" ", resume_text or "")
    cleaned = PHONE_RE.sub(" ", cleaned)
    cleaned = re.sub(r"(?:https?://|www\.)\S+", " ", cleaned, flags=re.I)
    metrics: list[str] = []
    seen: set[str] = set()
    for match in METRIC_RE.finditer(cleaned):
        raw = clean_line(match.group(0))
        if not raw or raw in seen:
            continue
        digits = re.sub(r"\D", "", raw)
        has_signal = bool(re.search(r"[₹$€£%+xkm]|million|billion|crore|lakh", raw, re.I))
        if not digits:
            continue
        if not has_signal:
            if len(digits) == 4:
                try:
                    number = int(digits)
                    if 1900 <= number <= 2099:
                        continue
                except ValueError:
                    pass
            if len(digits) >= 10 or int(digits) < 2:
                continue
        seen.add(raw)
        metrics.append(raw)
        if len(metrics) >= 12:
            break
    return metrics


def extract_action_verbs(resume_text: str) -> list[str]:
    text = resume_text or ""
    found: list[str] = []
    for verb in ACTION_VERBS:
        if re.search(rf"(?<![A-Za-z]){re.escape(verb)}(?![A-Za-z])", text, re.I):
            if verb not in found:
                found.append(verb)
    return found


def analyze_impact(resume_text: str) -> ImpactAnalysis:
    metrics = extract_metrics(resume_text)
    verbs = extract_action_verbs(resume_text)
    metric_points = int(round(15 * min(len(metrics) / 5, 1.0)))
    verb_points = int(round(15 * min(len(verbs) / 8, 1.0)))
    return {
        "points": max(0, min(metric_points + verb_points, 30)),
        "metrics": metrics,
        "verbs": verbs,
        "metric_points": metric_points,
        "verb_points": verb_points,
    }


def score_status(score: int) -> tuple[str, str]:
    if score >= 80:
        return "Excellent", "#22C55E"
    if score >= 55:
        return "Moderate", "#F59E0B"
    return "Low", "#EF4444"


def build_recommendations(
    keyword_result: dict[str, Any],
    structure: dict[str, Any],
    impact: dict[str, Any],
    overall: int,
) -> list[str]:
    recommendations: list[str] = []
    missing = keyword_result.get("missing", [])
    partial = keyword_result.get("partial", [])
    if missing:
        names = ", ".join(item["display"] for item in missing[:8])
        recommendations.append(
            f"Add the most important missing JD keywords naturally in Skills and Experience: {names}."
        )
    elif partial:
        names = ", ".join(item["display"] for item in partial[:6])
        recommendations.append(
            f"Strengthen partial keyword coverage for {names} by using the exact phrases from the job description."
        )
    elif keyword_result.get("total_terms", 0) == 0:
        recommendations.append(
            "Use a more specific job description so the audit can extract role-relevant technical keywords."
        )

    if structure["missing_sections"]:
        recommendations.append(
            "Add clearly labeled ATS section headers for: "
            + ", ".join(structure["missing_sections"])
            + "."
        )
    if not structure["linkedin_found"]:
        recommendations.append(
            "Include a full LinkedIn profile URL using the linkedin.com/in/ format in the contact block."
        )
    if not structure["portfolio_found"]:
        recommendations.append(
            "Add a GitHub or portfolio URL (for example github.com/yourname) to demonstrate verifiable work."
        )
    if len(impact["metrics"]) < 5:
        recommendations.append(
            "Quantify at least five achievements with numbers, percentages, currency values, or scale indicators such as [X%], $[X], or [#] users."
        )
    if len(impact["verbs"]) < 8:
        recommendations.append(
            "Start more bullets with varied strong action verbs such as Led, Engineered, Optimized, Automated, or Reduced."
        )
    if keyword_result["points"] < 30:
        recommendations.append(
            "Tailor the resume to this specific role by mirroring exact tool names and phrases from the JD where they truthfully apply."
        )
    if overall >= 85:
        recommendations.append(
            "The resume is strongly aligned. Keep the truthfulness and readability checks while tailoring keywords for each application."
        )
    if not recommendations:
        recommendations.append(
            "Maintain this structure, refresh metrics for each role, and re-run the audit after every tailored edit."
        )
    return recommendations[:8]


def run_ats_audit(resume_text: str, jd_text: str) -> AuditResult:
    keyword_result = analyze_keywords(resume_text, jd_text)
    structure = analyze_structure(resume_text)
    impact = analyze_impact(resume_text)
    overall = max(
        0,
        min(
            keyword_result["points"] + structure["points"] + impact["points"],
            100,
        ),
    )
    status, color = score_status(overall)
    word_count = len(re.findall(r"\b[\w'-]+\b", resume_text))

    passed: list[str] = []
    if structure["found_sections"]:
        passed.append(
            "ATS section headers detected: "
            + ", ".join(structure["found_sections"])
            + "."
        )
    if structure["email_found"] and structure["phone_found"]:
        passed.append("Contact details include both an email address and a phone number.")
    elif structure["email_found"]:
        passed.append("A professional email address was detected.")
    elif structure["phone_found"]:
        passed.append("A phone number was detected.")
    if structure["linkedin_found"]:
        passed.append("LinkedIn profile link detected in the expected linkedin.com/in/ format.")
    if structure["portfolio_found"]:
        passed.append("GitHub or portfolio link detected for verifiable project work.")
    if keyword_result["matched"]:
        names = ", ".join(item["display"] for item in keyword_result["matched"][:8])
        passed.append(
            f"{len(keyword_result['matched'])} of {keyword_result['total_terms']} extracted JD keywords are directly aligned: {names}."
        )
    if impact["metrics"]:
        passed.append(
            f"{len(impact['metrics'])} quantifiable metric signal(s) detected, including {', '.join(impact['metrics'][:5])}."
        )
    if impact["verbs"]:
        passed.append(
            f"{len(impact['verbs'])} strong action verb(s) detected, including {', '.join(impact['verbs'][:8])}."
        )
    passed.append(f"Resume text parsed successfully ({word_count:,} words).")

    recommendations = build_recommendations(keyword_result, structure, impact, overall)
    return {
        "overall": overall,
        "status": status,
        "color": color,
        "keyword": keyword_result,
        "structure": structure,
        "impact": impact,
        "passed": passed,
        "recommendations": recommendations,
        "word_count": word_count,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
