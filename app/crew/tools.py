"""Narrow, permission-checked tools exposed to specialized agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.job_search_ai.domain.jobs import JobRecord
from src.job_search_ai.domain.matching import match_job
from src.job_search_ai.domain.verification import VerificationResult

from ..storage import SQLiteStore


class ToolPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class AgentToolContext:
    agent_name: str
    permissions: frozenset[str]

    def require(self, tool_name: str) -> None:
        if tool_name not in self.permissions:
            raise ToolPermissionError(f"{self.agent_name} is not permitted to use {tool_name}")


def read_candidate_profile(context: AgentToolContext, profile_path: str | Path) -> dict:
    context.require("read_candidate_profile")
    import json
    data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    data.pop("contact", None)
    return data


def read_candidate_evidence(context: AgentToolContext, profile_path: str | Path) -> dict:
    context.require("read_candidate_evidence")
    profile = read_candidate_profile(context, profile_path)
    return {"projects": profile.get("projects", []), "skills": profile.get("skills", {})}


def save_job_record(context: AgentToolContext, store: SQLiteStore, job: JobRecord) -> None:
    context.require("save_job_record")
    store.save_job(job)


def find_duplicate_jobs(context: AgentToolContext, jobs: tuple[JobRecord, ...]) -> tuple[tuple[str, ...], ...]:
    context.require("find_duplicate_jobs")
    groups: dict[str, list[str]] = {}
    for job in jobs:
        groups.setdefault(job.fingerprint, []).append(job.record_id)
    return tuple(tuple(ids) for ids in groups.values() if len(ids) > 1)


def verify_source_url(context: AgentToolContext, source_url: str | None) -> bool:
    context.require("verify_source_url")
    parsed = urlparse(source_url or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def calculate_match_score(context: AgentToolContext, job: JobRecord, verification: VerificationResult, profile: dict) -> Any:
    context.require("calculate_match_score")
    return match_job(job, verification, profile)


def save_evaluation(context: AgentToolContext, store: SQLiteStore, evaluation: Any) -> None:
    context.require("save_evaluation")
    store.save_evaluation(evaluation)


def record_user_feedback(context: AgentToolContext, store: SQLiteStore, event: Any) -> None:
    context.require("record_user_feedback")
    store.save_memory_event(event)


def create_email_draft(context: AgentToolContext, subject: str, body: str, recipient: str | None = None) -> dict:
    context.require("create_email_draft")
    return {"type": "email_draft", "subject": subject, "body": body, "recipient": recipient, "status": "draft"}


def create_resume_draft(context: AgentToolContext, content: str, job_id: str) -> dict:
    context.require("create_resume_draft")
    return {"type": "resume_draft", "job_id": job_id, "content": content, "status": "draft"}


def default_permissions(agent_name: str) -> frozenset[str]:
    permissions = {
        "job_discovery": {"save_job_record", "find_duplicate_jobs", "verify_source_url"},
        "verification": {"verify_source_url", "find_duplicate_jobs"},
        "matching": {"read_candidate_profile", "read_candidate_evidence", "calculate_match_score"},
        "ranking": {"read_candidate_profile"},
        "resume": {"read_candidate_evidence", "create_resume_draft"},
        "application_strategist": {"read_candidate_profile", "create_email_draft"},
        "evaluator": {"read_candidate_profile", "save_evaluation"},
        "report": {"read_candidate_profile", "create_email_draft"},
    }
    return frozenset(permissions.get(agent_name, set()))
