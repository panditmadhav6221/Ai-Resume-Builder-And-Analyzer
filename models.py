from __future__ import annotations

from typing import TypedDict


class Profile(TypedDict):
    full_name: str
    professional_title: str
    email: str
    phone: str
    city_state: str
    linkedin: str
    github: str
    education: str


class ResumeContent(TypedDict):
    summary: str
    experience_bullets: list[str]
    skills: dict[str, list[str]]


class KeywordRecord(TypedDict):
    display: str
    category: str
    jd_freq: int
    resume_freq: int
    status: str
    quality: float


class KeywordAnalysis(TypedDict):
    points: int
    coverage: float
    terms: list[str]
    matched: list[KeywordRecord]
    partial: list[KeywordRecord]
    missing: list[KeywordRecord]
    detail: list[KeywordRecord]
    total_terms: int


class StructureAnalysis(TypedDict):
    points: int
    headers: dict[str, bool]
    email_found: bool
    phone_found: bool
    linkedin_found: bool
    github_found: bool
    portfolio_found: bool
    found_sections: list[str]
    missing_sections: list[str]
    header_points: int
    link_points: int


class ImpactAnalysis(TypedDict):
    points: int
    metrics: list[str]
    verbs: list[str]
    metric_points: int
    verb_points: int


class AuditResult(TypedDict):
    overall: int
    status: str
    color: str
    keyword: KeywordAnalysis
    structure: StructureAnalysis
    impact: ImpactAnalysis
    passed: list[str]
    recommendations: list[str]
    word_count: int
    created_at: str


class JDTerm(TypedDict):
    term: str
    display: str
    jd_freq: int
    word_count: int
    category: str
