"""Append-only memory and feedback-derived learning signals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal


EventType = Literal["preference_feedback", "application_outcome", "agent_feedback"]
PreferenceDirection = Literal["like", "dislike"]
OutcomeType = Literal["applied", "rejected", "interview", "offer", "withdrawn", "unknown"]


@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    event_type: EventType
    record_id: str | None
    created_at: str
    source: str
    payload: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PreferenceSignal:
    term: str
    direction: PreferenceDirection
    strength: float
    evidence_count: int
    event_ids: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeMetric:
    recommendation: str
    total: int
    interviews: int
    offers: int
    rejections: int
    interview_rate: float
    offer_rate: float


@dataclass(frozen=True)
class LearningSnapshot:
    snapshot_version: str
    preference_signals: tuple[PreferenceSignal, ...]
    outcome_metrics: tuple[OutcomeMetric, ...]
    unexplained_outcomes: int
    source_event_ids: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class MemoryLedger:
    """Small append-only event ledger; persistence is explicit and replayable."""

    def __init__(self, events: tuple[MemoryEvent, ...] = ()):
        self._events: list[MemoryEvent] = list(events)
        self._event_ids = {event.event_id for event in events}

    @property
    def events(self) -> tuple[MemoryEvent, ...]:
        return tuple(self._events)

    def append(self, event: MemoryEvent) -> bool:
        """Append once; duplicate event IDs are ignored for idempotent retries."""

        if event.event_id in self._event_ids:
            return False
        self._events.append(event)
        self._event_ids.add(event.event_id)
        return True

    def record_preference(
        self,
        *,
        event_id: str,
        record_id: str | None,
        direction: PreferenceDirection,
        terms: tuple[str, ...],
        source: str = "user",
        created_at: str | None = None,
    ) -> bool:
        return self.append(MemoryEvent(
            event_id=event_id,
            event_type="preference_feedback",
            record_id=record_id,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
            source=source,
            payload={"direction": direction, "terms": list(terms)},
        ))

    def record_outcome(
        self,
        *,
        event_id: str,
        record_id: str,
        outcome: OutcomeType,
        recommendation: str,
        reason: str | None = None,
        reason_confidence: float = 0.0,
        source: str = "user",
        created_at: str | None = None,
    ) -> bool:
        if not 0.0 <= reason_confidence <= 1.0:
            raise ValueError("reason_confidence must be between 0 and 1")
        return self.append(MemoryEvent(
            event_id=event_id,
            event_type="application_outcome",
            record_id=record_id,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
            source=source,
            payload={
                "outcome": outcome,
                "recommendation": recommendation,
                "reason": reason,
                "reason_confidence": reason_confidence,
            },
        ))

    def record_agent_feedback(
        self,
        *,
        event_id: str,
        record_id: str | None,
        agent_name: str,
        feedback: str,
        severity: str = "warning",
        source: str = "evaluator",
        created_at: str | None = None,
    ) -> bool:
        return self.append(MemoryEvent(
            event_id=event_id,
            event_type="agent_feedback",
            record_id=record_id,
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
            source=source,
            payload={"agent_name": agent_name, "feedback": feedback, "severity": severity},
        ))

    def derive_snapshot(self) -> LearningSnapshot:
        preference_totals: dict[str, float] = {}
        preference_events: dict[str, list[str]] = {}
        outcomes: dict[str, dict[str, int]] = {}
        unexplained = 0

        for event in self._events:
            if event.event_type == "preference_feedback":
                direction = event.payload.get("direction")
                delta = 1.0 if direction == "like" else -1.0
                for raw_term in event.payload.get("terms", ()):
                    term = str(raw_term).strip().casefold()
                    if not term:
                        continue
                    preference_totals[term] = preference_totals.get(term, 0.0) + delta
                    preference_events.setdefault(term, []).append(event.event_id)
            elif event.event_type == "application_outcome":
                recommendation = str(event.payload.get("recommendation", "unknown"))
                bucket = outcomes.setdefault(recommendation, {"total": 0, "interviews": 0, "offers": 0, "rejections": 0})
                bucket["total"] += 1
                outcome = event.payload.get("outcome")
                if outcome == "interview":
                    bucket["interviews"] += 1
                elif outcome == "offer":
                    bucket["offers"] += 1
                elif outcome == "rejected":
                    bucket["rejections"] += 1
                if outcome == "rejected" and not event.payload.get("reason"):
                    unexplained += 1

        signals = []
        for term, total in preference_totals.items():
            direction: PreferenceDirection = "like" if total > 0 else "dislike"
            signals.append(PreferenceSignal(
                term=term,
                direction=direction,
                strength=round(min(abs(total) / 3.0, 1.0), 3),
                evidence_count=len(preference_events[term]),
                event_ids=tuple(preference_events[term]),
            ))
        signals.sort(key=lambda signal: (-signal.strength, signal.term))

        metrics = []
        for recommendation, bucket in sorted(outcomes.items()):
            total = bucket["total"]
            metrics.append(OutcomeMetric(
                recommendation=recommendation,
                total=total,
                interviews=bucket["interviews"],
                offers=bucket["offers"],
                rejections=bucket["rejections"],
                interview_rate=round(bucket["interviews"] / total, 3) if total else 0.0,
                offer_rate=round(bucket["offers"] / total, 3) if total else 0.0,
            ))
        return LearningSnapshot(
            snapshot_version="1.0",
            preference_signals=tuple(signals),
            outcome_metrics=tuple(metrics),
            unexplained_outcomes=unexplained,
            source_event_ids=tuple(event.event_id for event in self._events),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def save_jsonl(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(event.to_dict(), ensure_ascii=False) + "\n" for event in self._events), encoding="utf-8")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> "MemoryLedger":
        target = Path(path)
        if not target.exists():
            return cls()
        events = []
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(MemoryEvent(**json.loads(line)))
        return cls(tuple(events))
