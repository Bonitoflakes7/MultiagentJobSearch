"""Dashboard view models and digest renderers.

This layer is intentionally side-effect free: it creates views and drafts but
does not send email or mutate application state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape

from ..domain.jobs import JobRecord
from ..domain.matching import MatchAnalysis
from ..domain.memory import LearningSnapshot
from ..domain.ranking import DailyActionPlan, RankingDecision
from ..domain.resume import ResumeAnalysis
from ..domain.verification import VerificationResult


@dataclass(frozen=True)
class DashboardJobCard:
    record_id: str
    rank: int
    tier: str
    title: str
    company: str
    location: str
    score: float
    confidence: float
    action: str
    why: tuple[str, ...]
    concerns: tuple[str, ...]
    skill_gaps: tuple[str, ...]


@dataclass(frozen=True)
class DashboardSnapshot:
    dashboard_version: str
    generated_at: str
    stats: dict[str, int]
    top_opportunities: tuple[DashboardJobCard, ...]
    daily_plan: DailyActionPlan
    preference_signals: tuple[dict, ...]
    outcome_metrics: tuple[dict, ...]
    alerts: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def build_dashboard(
    jobs: tuple[JobRecord, ...],
    verifications: tuple[VerificationResult, ...],
    matches: tuple[MatchAnalysis, ...],
    decisions: tuple[RankingDecision, ...],
    daily_plan: DailyActionPlan,
    resume_analyses: tuple[ResumeAnalysis, ...] = (),
    learning: LearningSnapshot | None = None,
    *,
    max_opportunities: int = 10,
) -> DashboardSnapshot:
    """Build a read-only dashboard snapshot from workflow results."""

    if max_opportunities < 1:
        raise ValueError("max_opportunities must be at least 1")
    verification_by_id = {item.record_id: item for item in verifications}
    match_by_id = {item.record_id: item for item in matches}
    job_by_id = {item.record_id: item for item in jobs}
    cards: list[DashboardJobCard] = []
    for decision in decisions[:max_opportunities]:
        match = match_by_id.get(decision.record_id)
        job = job_by_id.get(decision.record_id)
        if not match or not job:
            continue
        cards.append(DashboardJobCard(
            record_id=decision.record_id,
            rank=decision.rank,
            tier=decision.tier,
            title=decision.title or "Untitled role",
            company=decision.company or "Unknown company",
            location=job.location or "Unknown location",
            score=match.overall_score,
            confidence=match.confidence,
            action=decision.action,
            why=decision.rationale,
            concerns=decision.concerns,
            skill_gaps=match.missing_skills,
        ))

    verified = sum(1 for item in verifications if item.status == "verified")
    strong = sum(1 for item in decisions if item.tier in {"S", "A"})
    uncertain = sum(1 for item in verifications if item.status in {"uncertain", "needs_review"})
    application_total = sum(item.total for item in (learning.outcome_metrics if learning else ()))
    interview_total = sum(item.interviews for item in (learning.outcome_metrics if learning else ()))
    offer_total = sum(item.offers for item in (learning.outcome_metrics if learning else ()))
    stats = {
        "jobs_discovered": len(jobs),
        "verified_jobs": verified,
        "strong_matches": strong,
        "uncertain_jobs": uncertain,
        "applications_tracked": application_total,
        "interviews": interview_total,
        "offers": offer_total,
        "resume_reviews": len(resume_analyses),
    }
    alerts: list[str] = []
    if uncertain:
        alerts.append(f"{uncertain} job(s) need verification review before action.")
    if learning and learning.unexplained_outcomes:
        alerts.append(f"{learning.unexplained_outcomes} rejection outcome(s) have no known reason; do not over-correct the model.")
    if not cards:
        alerts.append("No ranked opportunity cards are available yet.")
    return DashboardSnapshot(
        dashboard_version="1.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        stats=stats,
        top_opportunities=tuple(cards),
        daily_plan=daily_plan,
        preference_signals=tuple(asdict(signal) for signal in (learning.preference_signals if learning else ())),
        outcome_metrics=tuple(asdict(metric) for metric in (learning.outcome_metrics if learning else ())),
        alerts=tuple(alerts),
    )


def render_digest_markdown(snapshot: DashboardSnapshot) -> str:
    """Render a human-readable digest draft without sending it."""

    lines = ["# Job Search Intelligence Digest", "", f"Generated: {snapshot.generated_at}", "", "## Summary", ""]
    lines.append(" | ".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in snapshot.stats.items()))
    lines.extend(["", "## Top opportunities", ""])
    if not snapshot.top_opportunities:
        lines.append("No opportunities are ready for review.")
    for card in snapshot.top_opportunities:
        lines.append(f"### #{card.rank} {card.title} — {card.company}")
        lines.append(f"Tier {card.tier} · Score {card.score:.1f}/100 · Confidence {card.confidence:.0%} · Action: **{card.action}**")
        if card.location:
            lines.append(f"Location: {card.location}")
        if card.why:
            lines.append("Why: " + "; ".join(card.why))
        if card.concerns:
            lines.append("Review: " + "; ".join(card.concerns))
        if card.skill_gaps:
            lines.append("Skill gaps: " + ", ".join(card.skill_gaps))
        lines.append("")
    lines.extend(["## Today's action plan", ""])
    if snapshot.daily_plan.actions:
        for action in snapshot.daily_plan.actions:
            lines.append(f"{action.order}. **{action.action}** — {action.title or 'Untitled role'} at {action.company or 'Unknown company'} ({action.estimated_effort_minutes} min): {action.reason}")
    else:
        lines.append("No actions selected.")
    if snapshot.alerts:
        lines.extend(["", "## Alerts", ""])
        lines.extend(f"- {alert}" for alert in snapshot.alerts)
    return "\n".join(lines) + "\n"


def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    """Render a small self-contained dashboard view for local preview."""

    stats = "".join(f"<li><strong>{escape(key.replace('_', ' ').title())}</strong>: {value}</li>" for key, value in snapshot.stats.items())
    cards = []
    for card in snapshot.top_opportunities:
        why = " ".join(escape(item) for item in card.why) or "No explanation available."
        concerns = "".join(f"<li>{escape(item)}</li>" for item in card.concerns)
        cards.append(
            f"<article class='job-card'><h2>#{card.rank} {escape(card.title)} — {escape(card.company)}</h2>"
            f"<p>Tier {escape(card.tier)} · Score {card.score:.1f}/100 · Confidence {card.confidence:.0%} · Action: {escape(card.action)}</p>"
            f"<p><strong>Why:</strong> {why}</p>"
            f"<ul>{concerns}</ul></article>"
        )
    alert_html = "".join(f"<li>{escape(alert)}</li>" for alert in snapshot.alerts)
    return "".join([
        "<!doctype html><html><head><meta charset='utf-8'><title>Job Search Intelligence</title>",
        "<style>body{font-family:system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}",
        ".job-card{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}",
        "li{margin:.35rem 0}</style></head><body>",
        "<h1>Job Search Intelligence</h1><h2>Summary</h2><ul>", stats, "</ul>",
        "<h2>Top opportunities</h2>", "".join(cards) or "<p>No opportunities are ready.</p>",
        "<h2>Alerts</h2><ul>", alert_html or "<li>None</li>", "</ul></body></html>",
    ])
