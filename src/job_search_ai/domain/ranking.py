"""Ranking and daily action planning for matched jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Literal

from .jobs import JobRecord
from .matching import MatchAnalysis
from .verification import VerificationResult, _parse_date


Tier = Literal["S", "A", "B", "C", "D"]
ActionType = Literal["apply", "review_verification", "tailor_resume", "monitor", "skip"]


@dataclass(frozen=True)
class RankingDecision:
    record_id: str
    title: str | None
    company: str | None
    rank: int
    priority_score: float
    tier: Tier
    action: ActionType
    rationale: tuple[str, ...]
    concerns: tuple[str, ...]
    score_breakdown: dict[str, float]


@dataclass(frozen=True)
class DailyAction:
    order: int
    record_id: str
    action: ActionType
    title: str | None
    company: str | None
    reason: str
    estimated_effort_minutes: int


@dataclass(frozen=True)
class DailyActionPlan:
    plan_version: str
    as_of: str
    actions: tuple[DailyAction, ...]
    ranked_jobs: tuple[RankingDecision, ...]
    omitted_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def _freshness_score(job: JobRecord, as_of: date) -> float:
    posted = _parse_date(job.posting_date, as_of)
    if not posted:
        return 45.0
    age = (as_of - posted).days
    if age < 0:
        return 35.0
    if age <= 3:
        return 100.0
    if age <= 7:
        return 90.0
    if age <= 14:
        return 75.0
    if age <= 30:
        return 55.0
    return 20.0


def _action_for(match: MatchAnalysis, verification: VerificationResult) -> ActionType:
    if match.recommendation == "blocked" or verification.status == "rejected":
        return "skip"
    if verification.status in {"uncertain", "needs_review"}:
        return "review_verification"
    if match.recommendation == "apply_priority":
        return "apply"
    if match.recommendation in {"apply_review", "stretch_review"} and match.missing_skills:
        return "tailor_resume"
    if match.recommendation == "do_not_prioritize":
        return "monitor"
    return "review_verification"


def _tier(score: float, action: ActionType) -> Tier:
    if action == "skip":
        return "D"
    if score >= 85:
        return "S"
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    if score >= 45:
        return "C"
    return "D"


def rank_jobs(
    items: tuple[tuple[JobRecord, MatchAnalysis, VerificationResult], ...],
    *,
    as_of: date | None = None,
) -> tuple[RankingDecision, ...]:
    """Rank jobs deterministically using match quality plus operational value."""

    as_of = as_of or datetime.now(timezone.utc).date()
    pending: list[tuple[float, JobRecord, MatchAnalysis, VerificationResult, dict[str, float], ActionType]] = []
    for job, match, verification in items:
        freshness = _freshness_score(job, as_of)
        verification_quality = {"verified": 100.0, "uncertain": 50.0, "needs_review": 0.0, "rejected": 0.0}[verification.status]
        confidence = match.confidence * 100
        priority = (match.overall_score * 0.65) + (confidence * 0.15) + (freshness * 0.10) + (verification_quality * 0.10)
        action = _action_for(match, verification)
        if action == "skip":
            priority = 0.0
        breakdown = {
            "match": round(match.overall_score, 2),
            "confidence": round(confidence, 2),
            "freshness": round(freshness, 2),
            "verification_quality": verification_quality,
        }
        pending.append((round(priority, 2), job, match, verification, breakdown, action))

    pending.sort(key=lambda item: (-item[0], -item[2].confidence, item[1].record_id))
    decisions: list[RankingDecision] = []
    for index, (priority, job, match, verification, breakdown, action) in enumerate(pending, start=1):
        rationale: list[str] = []
        concerns: list[str] = list(match.warnings)
        if match.overall_score >= 80:
            rationale.append(f"Strong fit score: {match.overall_score:.1f}/100")
        elif match.overall_score >= 60:
            rationale.append(f"Usable fit score: {match.overall_score:.1f}/100")
        if breakdown["freshness"] >= 90:
            rationale.append("Fresh listing")
        elif breakdown["freshness"] <= 45:
            concerns.append("Freshness is unknown or low")
        if verification.status == "verified":
            rationale.append("Passed current verification gates")
        else:
            concerns.append(f"Verification status: {verification.status}")
        if match.missing_skills:
            concerns.append("Skill gaps: " + ", ".join(match.missing_skills))
        decisions.append(RankingDecision(
            record_id=job.record_id,
            title=job.title,
            company=job.company,
            rank=index,
            priority_score=priority,
            tier=_tier(priority, action),
            action=action,
            rationale=tuple(dict.fromkeys(rationale)),
            concerns=tuple(dict.fromkeys(concerns)),
            score_breakdown=breakdown,
        ))
    return tuple(decisions)


def build_daily_plan(
    decisions: tuple[RankingDecision, ...],
    *,
    as_of: date | None = None,
    max_actions: int = 5,
) -> DailyActionPlan:
    """Select a small, actionable queue without pretending all jobs are equal."""

    if max_actions < 1:
        raise ValueError("max_actions must be at least 1")
    as_of = as_of or datetime.now(timezone.utc).date()
    candidates = [item for item in decisions if item.action != "skip"][:max_actions]
    actions: list[DailyAction] = []
    for index, decision in enumerate(candidates, start=1):
        effort = {"apply": 20, "review_verification": 8, "tailor_resume": 35, "monitor": 3}.get(decision.action, 10)
        reason = decision.rationale[0] if decision.rationale else "Highest remaining actionable priority"
        if decision.concerns:
            reason += "; review: " + decision.concerns[0]
        actions.append(DailyAction(index, decision.record_id, decision.action, decision.title, decision.company, reason, effort))
    return DailyActionPlan(
        plan_version="1.0",
        as_of=as_of.isoformat(),
        actions=tuple(actions),
        ranked_jobs=decisions,
        omitted_count=max(0, len([item for item in decisions if item.action != "skip"]) - len(actions)),
    )
