"""Human-in-the-loop decisions and outcome boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

from ..infrastructure.actions import ActionRequest, create_action_request


HumanDecisionType = Literal[
    "approve_recommendation", "reject_recommendation", "interested",
    "not_interested", "already_applied",
]
OutcomeType = Literal["unknown", "applied", "rejected", "interview", "offer", "withdrawn"]


@dataclass(frozen=True)
class HumanDecision:
    decision_id: str
    record_id: str
    decision: HumanDecisionType
    actor: str
    created_at: str
    note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class JobInteractionState:
    """Explicitly separates AI recommendation, human decision, action, outcome."""

    record_id: str
    ai_recommendation: str
    human_decision: str = "not_recorded"
    external_action: str = "not_requested"
    outcome: OutcomeType = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


def record_human_decision(
    record_id: str,
    decision: HumanDecisionType,
    *,
    decision_id: str,
    actor: str = "user",
    note: str | None = None,
) -> HumanDecision:
    if not record_id.strip():
        raise ValueError("record_id is required")
    if not decision_id.strip():
        raise ValueError("decision_id is required")
    return HumanDecision(decision_id, record_id, decision, actor, datetime.now(timezone.utc).isoformat(), note)


def prepare_application_action(
    recommendation: str,
    decision: HumanDecision,
    *,
    action_id: str,
    target: str,
    payload: str,
) -> ActionRequest:
    """Prepare, but never execute, an external application action."""

    if recommendation != "apply":
        raise PermissionError("only an apply recommendation can be prepared as an application action")
    if decision.decision not in {"approve_recommendation", "already_applied"}:
        raise PermissionError("human approval is required before preparing an application action")
    return create_action_request(action_id, "submit_application", target, payload)
