"""Canonical job records and deterministic text normalization.

This module deliberately does not browse the web or call an LLM. It converts
user-provided job text and URL metadata into a stable record that later agents
can inspect.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import re
from typing import Literal
from urllib.parse import urlparse


SourceKind = Literal["paste", "url"]
JobStatus = Literal["candidate", "needs_enrichment"]


@dataclass(frozen=True)
class JobInput:
    """Untrusted input supplied by a user or a source adapter."""

    source_kind: SourceKind
    raw_text: str = ""
    source_url: str | None = None
    source_name: str | None = None
    discovered_at: str | None = None


@dataclass(frozen=True)
class JobRecord:
    """Normalized job data used by later workflow stages."""

    record_id: str
    fingerprint: str
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    experience_min_years: float | None
    experience_max_years: float | None
    salary_text: str | None
    posting_date: str | None
    source_kind: SourceKind
    source_name: str | None
    source_url: str | None
    skills: tuple[str, ...]
    responsibilities: tuple[str, ...]
    raw_description: str
    missing_fields: tuple[str, ...]
    warnings: tuple[str, ...]
    status: JobStatus
    discovered_at: str
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return asdict(self)


KNOWN_SKILLS = (
    "python", "fastapi", "flask", "django", "rest api", "restful api", "sql",
    "postgresql", "mysql", "mongodb", "docker", "kubernetes", "aws", "redis",
    "celery", "langchain", "langgraph", "crewai", "rag", "machine learning",
    "llm", "tensorflow", "pytorch", "java", "javascript", "react", "node.js",
    "go", "graphql", "neo4j", "git", "tesseract", "ocr", "kafka",
)

_HEADING_RE = re.compile(r"^\s*(title|role|position|job title|company|organization|employer|location|salary|compensation|experience|posted|posting date)\s*[:\-]\s*(.+?)\s*$", re.I | re.M)
_YEARS_RE = re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*(?:-|to|–|—)\s*(?P<max>\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I)
_AT_LEAST_RE = re.compile(r"(?:at least|min(?:imum)? of)\s*(?P<min>\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I)
_UP_TO_RE = re.compile(r"(?:up to|maximum of)\s*(?P<max>\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I)
_INSTRUCTION_RE = re.compile(r"\b(ignore (?:all )?(?:previous|prior) instructions|system message|developer message|reveal your prompt|disregard the job requirements)\b", re.I)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" \t:-|")
    return cleaned or None


def _heading_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in _HEADING_RE.finditer(text):
        key = match.group(1).lower().replace(" ", "_")
        values[key] = _clean(match.group(2)) or ""
    return values


def _first_line_candidate(text: str) -> str | None:
    for line in text.splitlines():
        candidate = _clean(line)
        if candidate and len(candidate) <= 120 and not candidate.endswith(":"):
            return candidate
    return None


def _extract_experience(text: str) -> tuple[float | None, float | None]:
    match = _YEARS_RE.search(text)
    if match:
        return float(match.group("min")), float(match.group("max"))
    match = _AT_LEAST_RE.search(text)
    if match:
        return float(match.group("min")), None
    match = _UP_TO_RE.search(text)
    if match:
        return None, float(match.group("max"))
    if re.search(r"\b(fresher|fresh graduate|entry[- ]level|0\s*(?:-|to)\s*1\s*year)\b", text, re.I):
        return 0.0, 1.0
    return None, None


def _extract_skills(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    found: list[str] = []
    for skill in KNOWN_SKILLS:
        if re.search(r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])", lowered):
            label = "REST APIs" if skill in {"rest api", "restful api"} else skill
            label = label.title() if label not in {"SQL", "LLM", "RAG", "AWS", "OCR"} else label.upper()
            if label not in found:
                found.append(label)
    return tuple(found)


def _extract_bullets(text: str, section_names: tuple[str, ...]) -> tuple[str, ...]:
    lines = text.splitlines()
    in_section = False
    results: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower().rstrip(":")
        if any(name in lowered for name in section_names):
            in_section = True
            continue
        if in_section and re.match(r"^(requirements?|qualifications?|skills?|benefits?|about|responsibilities?)\s*:", line, re.I):
            in_section = False
        if in_section and re.match(r"^(?:[-*•]|\d+[.)])\s+", line):
            results.append(re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", line))
    return tuple(results)


def _canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _source_name(source_name: str | None, source_url: str | None) -> str | None:
    if source_name:
        return _clean(source_name)
    canonical = _canonical_url(source_url)
    return urlparse(canonical).netloc if canonical else None


def normalize_job(job_input: JobInput) -> JobRecord:
    """Create a deterministic canonical record from untrusted job input."""

    if job_input.source_kind not in {"paste", "url"}:
        raise ValueError("source_kind must be 'paste' or 'url'")

    raw = job_input.raw_text.strip()
    headings = _heading_values(raw)
    title = headings.get("title") or headings.get("role") or headings.get("position") or headings.get("job_title")
    company = headings.get("company") or headings.get("organization") or headings.get("employer")
    location = headings.get("location")
    salary = headings.get("salary") or headings.get("compensation")
    posting_date = headings.get("posted") or headings.get("posting_date")

    first_line = _first_line_candidate(raw)
    if not title and first_line and not re.search(r"\b(company|location|salary|experience)\b\s*:", first_line, re.I):
        title = first_line

    min_years, max_years = _extract_experience(raw)
    normalized_url = _canonical_url(job_input.source_url)
    skills = _extract_skills(raw)
    responsibilities = _extract_bullets(raw, ("responsibilities", "what you will do", "what you'll do", "role overview"))
    warnings: list[str] = []
    missing: list[str] = []

    if not title:
        missing.append("title")
    if not company:
        missing.append("company")
    if not location:
        missing.append("location")
    if not raw:
        missing.append("description")
        warnings.append("description_not_provided")
    if job_input.source_kind == "url" and not normalized_url:
        warnings.append("invalid_or_missing_source_url")
    if job_input.source_kind == "paste" and not normalized_url:
        missing.append("source_url")
    if not skills:
        warnings.append("no_known_skills_detected")
    if _INSTRUCTION_RE.search(raw):
        warnings.append("embedded_agent_instructions_detected_do_not_follow")

    # Prefer role identity fields so the same listing copied across sources can
    # converge to one fingerprint. Fall back to URL/raw text when those fields
    # are unavailable rather than inventing an identity.
    core_identity = "|".join((title or "", company or "", location or "", posting_date or ""))
    identity = core_identity if any((title, company, location, posting_date)) else "|".join((normalized_url or "", raw[:500].lower()))
    fingerprint = sha256(re.sub(r"\s+", " ", identity).strip().encode("utf-8")).hexdigest()[:24]
    discovered_at = job_input.discovered_at or datetime.now(timezone.utc).isoformat()
    status: JobStatus = "needs_enrichment" if missing or not raw else "candidate"

    return JobRecord(
        record_id=f"job_{fingerprint}",
        fingerprint=fingerprint,
        title=title,
        company=company,
        location=location,
        employment_type=None,
        experience_min_years=min_years,
        experience_max_years=max_years,
        salary_text=salary,
        posting_date=posting_date,
        source_kind=job_input.source_kind,
        source_name=_source_name(job_input.source_name, normalized_url),
        source_url=normalized_url,
        skills=skills,
        responsibilities=responsibilities,
        raw_description=raw,
        missing_fields=tuple(dict.fromkeys(missing)),
        warnings=tuple(dict.fromkeys(warnings)),
        status=status,
        discovered_at=discovered_at,
    )
