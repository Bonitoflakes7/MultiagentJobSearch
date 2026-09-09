"""Deterministic verification and safety gates for normalized jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import re
from typing import Literal
from urllib.parse import urlparse

from .jobs import JobRecord


CheckStatus = Literal["pass", "fail", "uncertain", "not_checked"]
VerificationStatus = Literal["verified", "uncertain", "rejected", "needs_review"]


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    status: CheckStatus
    reason: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    record_id: str
    verification_version: str
    status: VerificationStatus
    checks: tuple[VerificationCheck, ...]
    blocking_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    verified_at: str

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_TARGET_ROLE_TERMS = (
    "python developer", "software developer", "software engineer", "ai engineer",
    "ai developer", "backend developer", "backend engineer", "machine learning engineer",
    "ml engineer", "research engineer", "developer intern", "software intern",
    "backend intern", "python intern", "ai intern", "ml intern",
)

_SENIOR_TERMS = re.compile(r"\b(senior|sr\.?|lead|principal|staff|architect|manager|director|head of)\b", re.I)
_INJECTION_TERMS = re.compile(r"\b(ignore (?:all )?(?:previous|prior) instructions|reveal your prompt|system message|developer message)\b", re.I)
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y")


def _parse_date(value: str | None, reference: date | None = None) -> date | None:
    if not value:
        return None
    cleaned = value.strip()
    reference = reference or datetime.now(timezone.utc).date()
    relative = re.fullmatch(r"(?:(\d+)\s+days?\s+ago|yesterday|today|just\s+posted)", cleaned, re.I)
    if relative:
        if relative.group(1):
            return reference - timedelta(days=int(relative.group(1)))
        if cleaned.casefold() == "yesterday":
            return reference - timedelta(days=1)
        return reference
    weeks = re.fullmatch(r"(\d+)\s+weeks?\s+ago", cleaned, re.I)
    if weeks:
        return reference - timedelta(weeks=int(weeks.group(1)))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _check_url(record: JobRecord) -> VerificationCheck:
    if not record.source_url:
        return VerificationCheck("source_url", "uncertain", "No source URL was provided; live listing verification is not possible.")
    parsed = urlparse(record.source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return VerificationCheck("source_url", "fail", "Source URL is not a valid HTTP(S) URL.", (record.source_url,))
    return VerificationCheck("source_url", "pass", "Source URL has a valid HTTP(S) shape.", (record.source_url,))


def _check_completeness(record: JobRecord) -> VerificationCheck:
    required = {"title", "company", "location", "description"}
    missing = sorted(required.intersection(record.missing_fields))
    if missing:
        return VerificationCheck("completeness", "uncertain", "Required fields are missing.", tuple(missing))
    return VerificationCheck("completeness", "pass", "Required fields are present.")


def _check_freshness(record: JobRecord, as_of: date, max_age_days: int) -> VerificationCheck:
    if not record.posting_date:
        return VerificationCheck("freshness", "uncertain", "Posting date is not supplied.")
    posted = _parse_date(record.posting_date, as_of)
    if not posted:
        return VerificationCheck("freshness", "uncertain", "Posting date could not be parsed.", (record.posting_date,))
    if posted > as_of:
        return VerificationCheck("freshness", "uncertain", "Posting date is in the future; requires review.", (record.posting_date,))
    age = (as_of - posted).days
    if age > max_age_days:
        return VerificationCheck("freshness", "fail", f"Listing is {age} days old, beyond the {max_age_days}-day freshness window.", (record.posting_date,))
    return VerificationCheck("freshness", "pass", f"Listing is {age} days old.", (record.posting_date,))


def _check_location(record: JobRecord, preferred_locations: tuple[str, ...]) -> VerificationCheck:
    if not record.location:
        return VerificationCheck("location", "uncertain", "Location is missing.")
    location = record.location.casefold()
    matches = tuple(item for item in preferred_locations if item.casefold() in location or location in item.casefold())
    if matches:
        return VerificationCheck("location", "pass", "Location matches a preferred location.", matches)
    if "remote" in location and not preferred_locations:
        return VerificationCheck("location", "uncertain", "Remote work is present but no location policy was supplied.")
    return VerificationCheck("location", "uncertain", "Location does not match a preferred location; human review is required.", (record.location,))


def _check_experience(record: JobRecord, max_candidate_years: float) -> VerificationCheck:
    text = f"{record.title or ''} {record.raw_description}"
    if _SENIOR_TERMS.search(text):
        return VerificationCheck("experience", "fail", "Role contains a seniority signal outside the fresher/0-1 year target.")
    if record.experience_min_years is not None and record.experience_min_years > max_candidate_years:
        return VerificationCheck("experience", "fail", "Minimum required experience exceeds the candidate target band.", (str(record.experience_min_years),))
    if record.experience_min_years is None and record.experience_max_years is None:
        return VerificationCheck("experience", "uncertain", "Experience requirement is not stated.")
    return VerificationCheck("experience", "pass", "Experience requirement is compatible with the target band.")


def _check_relevance(record: JobRecord, target_role_terms: tuple[str, ...]) -> VerificationCheck:
    text = f"{record.title or ''} {record.raw_description}".casefold()
    matches = tuple(term for term in target_role_terms if term.casefold() in text)
    if matches:
        return VerificationCheck("role_relevance", "pass", "Role matches at least one target-role term.", matches)
    return VerificationCheck("role_relevance", "uncertain", "No target-role term was detected; do not discard automatically.")


def _check_safety(record: JobRecord) -> VerificationCheck:
    if "embedded_agent_instructions_detected_do_not_follow" in record.warnings or _INJECTION_TERMS.search(record.raw_description):
        return VerificationCheck("content_safety", "fail", "Job text contains instructions aimed at the agent and must be treated as untrusted content.")
    return VerificationCheck("content_safety", "pass", "No known agent-directed instruction pattern was detected.")


def verify_job(
    record: JobRecord,
    *,
    preferred_locations: tuple[str, ...] = ("Bangalore", "Kerala", "Pune"),
    max_candidate_years: float = 1.0,
    target_role_terms: tuple[str, ...] = DEFAULT_TARGET_ROLE_TERMS,
    as_of: date | None = None,
    max_age_days: int = 7,
) -> VerificationResult:
    """Run offline checks; network-dependent checks remain explicitly unverified."""

    as_of = as_of or datetime.now(timezone.utc).date()
    checks = (
        _check_url(record),
        _check_completeness(record),
        _check_freshness(record, as_of, max_age_days),
        _check_location(record, preferred_locations),
        _check_experience(record, max_candidate_years),
        _check_relevance(record, target_role_terms),
        _check_safety(record),
    )
    blocking = tuple(check.reason for check in checks if check.status == "fail")
    uncertain = tuple(check.reason for check in checks if check.status == "uncertain")
    if any(check.name == "content_safety" and check.status == "fail" for check in checks):
        status: VerificationStatus = "needs_review"
    elif blocking:
        status = "rejected"
    elif uncertain:
        status = "uncertain"
    else:
        status = "verified"
    return VerificationResult(
        record_id=record.record_id,
        verification_version="1.0",
        status=status,
        checks=checks,
        blocking_reasons=blocking,
        review_reasons=uncertain,
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


def find_duplicate_groups(records: tuple[JobRecord, ...]) -> tuple[tuple[str, ...], ...]:
    """Return groups of record IDs sharing a normalized fingerprint."""

    groups: dict[str, list[str]] = {}
    for record in records:
        groups.setdefault(record.fingerprint, []).append(record.record_id)
    return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)
