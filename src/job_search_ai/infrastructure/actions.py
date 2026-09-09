"""Human approval gates for consequential outbound actions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Literal

from .reliability import IdempotencyLedger


ActionType = Literal["send_email", "submit_application", "export_resume"]
ActionStatus = Literal["prepared", "approved", "executed"]


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    action_type: ActionType
    target: str
    payload_hash: str
    status: ActionStatus


def create_action_request(action_id: str, action_type: ActionType, target: str, payload: str) -> ActionRequest:
    return ActionRequest(action_id, action_type, target, sha256(payload.encode("utf-8")).hexdigest(), "prepared")


class ApprovalGate:
    def __init__(self, idempotency: IdempotencyLedger | None = None):
        self._actions: dict[str, ActionRequest] = {}
        self._idempotency = idempotency or IdempotencyLedger()

    def prepare(self, request: ActionRequest) -> ActionRequest:
        existing = self._actions.get(request.action_id)
        if existing and existing.payload_hash != request.payload_hash:
            raise ValueError("action_id already exists with a different payload")
        self._actions[request.action_id] = existing or request
        return self._actions[request.action_id]

    def approve(self, action_id: str) -> ActionRequest:
        request = self._actions.get(action_id)
        if not request:
            raise KeyError(action_id)
        approved = ActionRequest(request.action_id, request.action_type, request.target, request.payload_hash, "approved")
        self._actions[action_id] = approved
        return approved

    def execute(self, action_id: str, executor: Callable[[], str]) -> str:
        request = self._actions.get(action_id)
        if not request:
            raise KeyError(action_id)
        if self._idempotency.has_completed(action_id):
            raise RuntimeError("action was already executed")
        if request.status != "approved":
            raise PermissionError("action requires explicit approval")
        if not self._idempotency.mark_completed(action_id):
            raise RuntimeError("action was already executed")
        result = executor()
        self._actions[action_id] = ActionRequest(request.action_id, request.action_type, request.target, request.payload_hash, "executed")
        return result
