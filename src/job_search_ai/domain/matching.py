"""Explainable candidate-to-job matching.

This is the deterministic baseline. Later model-based agents may add richer
evidence extraction, but they must produce the same explainable result shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Literal

from .jobs import JobRecord
from .verification import VerificationResult


Recommendation = Literal["apply_priority", "apply_review", "stretch_review", "do_not_prioritize", "blocked"]


@dataclass(frozen=True)
class DimensionScore:
    name: str
    score: float
    weight: float
    evidence: tuple[str, ...]
    gaps: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class MatchAnalysis:
    record_id: str
    matching_version: str
    overall_score: float
    confidence: float
    recommendation: Recommendation
    dimensions: tuple[DimensionScore, ...]
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    hard_constraints: tuple[str, ...]
    warnings: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


ROLE_ALIASES = {
    "python": ("python developer", "python engineer", "python intern"),
    "backend": ("backend developer", "backend engineer", "backend intern"),
    "software": ("software developer", "software engineer", "software intern"),
    "ai": ("ai engineer", "ai developer", "ai intern"),
    "ml": ("machine learning engineer", "ml engineer", "ml intern"),
    "research": ("research engineer", "research intern"),
}


def load_candidate_profile(path: str | Path) -> dict:
    """Load the persisted profile without exposing contact fields to matching."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("contact", None)
    return data


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", " ", value.casefold()).strip()


def _contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def _job_text(job: JobRecord) -> str:
    return " ".join(filter(None, (job.title, job.company, job.location, job.raw_description))).casefold()


def _candidate_skills(profile: dict) -> set[str]:
    skills = profile.get("skills", {})
    values: list[str] = []
    for key in ("primary", "additional", "secondary_or_contextual"):
        values.extend(skills.get(key, []))
    return {_norm(skill) for skill in values}


def _skill_match(job: JobRecord, profile: dict) -> tuple[float, tuple[str, ...], tuple[str, ...], float]:
    candidate = _candidate_skills(profile)
    job_skill_labels = {_norm(skill): skill for skill in job.skills}
    job_skills = set(job_skill_labels)
    if not job_skills:
        return 50.0, (), ("Job skills were not detected",), 0.45

    # Use exact normalized labels here. Substring matching would incorrectly
    # treat JavaScript as Java, or Flask as a fragment of another term.
    matched = sorted(skill for skill in job_skills if skill in candidate)
    missing = sorted(job_skills - set(matched))
    score = round((len(matched) / len(job_skills)) * 100, 2)
    confidence = 0.9 if job_skills else 0.45
    return score, tuple(job_skill_labels[item] for item in matched), tuple(job_skill_labels[item] for item in missing), confidence


def _role_score(job: JobRecord, profile: dict) -> DimensionScore:
    title = (job.title or "").casefold()
    targets = profile.get("search_preferences", {}).get("target_roles", [])
    exact = [role for role in targets if role.casefold() in title]
    family_matches: list[str] = []
    for family, aliases in ROLE_ALIASES.items():
        if any(alias in title for alias in aliases):
            family_matches.append(family)
    if exact:
        return DimensionScore("role_relevance", 100.0, 0.25, tuple(f"Target role: {item}" for item in exact), (), 0.95)
    if family_matches:
        return DimensionScore("role_relevance", 85.0, 0.25, tuple(f"Related role family: {item}" for item in family_matches), (), 0.82)
    if any(term.casefold() in _job_text(job) for term in targets):
        return DimensionScore("role_relevance", 65.0, 0.25, ("Target-role language appears in the description",), (), 0.65)
    return DimensionScore("role_relevance", 25.0, 0.25, (), ("No target role or related role family detected",), 0.7)


def _experience_score(job: JobRecord) -> DimensionScore:
    if job.experience_min_years is not None and job.experience_min_years > 1:
        return DimensionScore("experience_compatibility", 0.0, 0.20, (), (f"Requires at least {job.experience_min_years:g} years",), 0.95)
    if job.experience_min_years is not None or job.experience_max_years is not None:
        return DimensionScore("experience_compatibility", 100.0, 0.20, ("Requirement fits the fresher/0-1 year band",), (), 0.9)
    return DimensionScore("experience_compatibility", 55.0, 0.20, (), ("Experience requirement is unspecified",), 0.55)


def _location_score(job: JobRecord, profile: dict) -> DimensionScore:
    preferred = profile.get("search_preferences", {}).get("locations", [])
    if not job.location:
        return DimensionScore("location_compatibility", 45.0, 0.15, (), ("Location is missing",), 0.45)
    matches = [item for item in preferred if item.casefold() in job.location.casefold() or job.location.casefold() in item.casefold()]
    if matches:
        return DimensionScore("location_compatibility", 100.0, 0.15, tuple(f"Preferred location: {item}" for item in matches), (), 0.95)
    return DimensionScore("location_compatibility", 35.0, 0.15, (), (f"Location is outside the preferred list: {job.location}",), 0.9)


def _domain_score(job: JobRecord, profile: dict) -> DimensionScore:
    text = _job_text(job)
    candidate_projects = profile.get("projects", [])
    project_terms = {term.casefold() for project in candidate_projects for term in project.get("technologies", [])}
    domain_terms = ("ai", "llm", "rag", "agent", "backend", "api", "machine learning", "clinical", "document intelligence")
    matched = sorted(term for term in domain_terms if term in text and (term in project_terms or term in {"ai", "backend", "api", "llm", "rag", "agent"}))
    if matched:
        return DimensionScore("domain_and_project_evidence", 90.0, 0.10, tuple(f"Relevant evidence: {item}" for item in matched), (), 0.8)
    return DimensionScore("domain_and_project_evidence", 55.0, 0.10, (), ("No strong domain overlap detected",), 0.55)


def match_job(job: JobRecord, verification: VerificationResult, profile: dict) -> MatchAnalysis:
    """Score a job using only the supplied job, verification, and profile snapshots."""

    if verification.status == "rejected":
        return MatchAnalysis(
            record_id=job.record_id,
            matching_version="1.0",
            overall_score=0.0,
            confidence=0.98,
            recommendation="blocked",
            dimensions=(),
            matched_skills=(),
            missing_skills=(),
            hard_constraints=verification.blocking_reasons,
            warnings=("Matching blocked because verification rejected the listing",),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    role = _role_score(job, profile)
    skills_score, matched_skills, missing_skills, skills_confidence = _skill_match(job, profile)
    skills = DimensionScore(
        "skill_match", skills_score, 0.30,
        tuple(f"Matched skill: {item}" for item in matched_skills),
        tuple(f"Skill gap: {item}" for item in missing_skills),
        skills_confidence,
    )
    experience = _experience_score(job)
    location = _location_score(job, profile)
    domain = _domain_score(job, profile)
    dimensions = (role, skills, experience, location, domain)
    overall = round(sum(item.score * item.weight for item in dimensions), 2)
    confidence = sum(item.confidence * item.weight for item in dimensions)
    if verification.status == "uncertain":
        confidence *= 0.85
    confidence = round(confidence, 2)
    warnings = list(verification.review_reasons)
    if verification.status == "uncertain":
        warnings.append("Verification is uncertain; score requires human review")
    if missing_skills:
        warnings.append("Missing skills are gaps, not evidence that the candidate cannot learn them")

    if verification.status == "needs_review":
        recommendation: Recommendation = "blocked"
    elif overall >= 80:
        recommendation = "apply_priority"
    elif overall >= 65:
        recommendation = "apply_review"
    elif overall >= 50:
        recommendation = "stretch_review"
    else:
        recommendation = "do_not_prioritize"
    return MatchAnalysis(
        record_id=job.record_id,
        matching_version="1.0",
        overall_score=overall,
        confidence=confidence,
        recommendation=recommendation,
        dimensions=dimensions,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        hard_constraints=(),
        warnings=tuple(dict.fromkeys(warnings)),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
