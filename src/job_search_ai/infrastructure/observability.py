"""Small redacted trace recorder for workflow diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    component: str
    event: str
    metadata: dict
    created_at: str


class TraceRecorder:
    def __init__(self):
        self.events: list[TraceEvent] = []

    def record(self, run_id: str, component: str, event: str, metadata: dict | None = None) -> TraceEvent:
        safe = {}
        for key, value in (metadata or {}).items():
            lowered = key.casefold()
            safe[key] = "[REDACTED]" if any(term in lowered for term in ("secret", "token", "password", "api_key")) else value
        trace = TraceEvent(run_id, component, event, safe, datetime.now(timezone.utc).isoformat())
        self.events.append(trace)
        return trace

    def save_jsonl(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("".join(json.dumps(asdict(event), ensure_ascii=False) + "\n" for event in self.events), encoding="utf-8")

