"""SQLite persistence for workflow state and immutable result snapshots."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from .pipeline import PipelineResult


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_profiles (
    profile_version TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    record_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_results (
    record_id TEXT NOT NULL,
    verification_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (record_id, verification_version)
);

CREATE TABLE IF NOT EXISTS match_analyses (
    record_id TEXT NOT NULL,
    matching_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (record_id, matching_version)
);

CREATE TABLE IF NOT EXISTS resume_analyses (
    record_id TEXT NOT NULL,
    resume_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (record_id, resume_version)
);

CREATE TABLE IF NOT EXISTS ranking_decisions (
    run_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, record_id),
    FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
);

CREATE TABLE IF NOT EXISTS agent_evaluations (
    output_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (output_id, agent_name, evaluator_version)
);

CREATE TABLE IF NOT EXISTS memory_events (
    event_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_requests (
    action_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS application_outcomes (
    event_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS human_decisions (
    decision_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    actor TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SQLiteStore:
    """Small durable repository with immutable snapshot semantics."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # CrewAI Flow listeners may execute in worker threads.  The store is
        # owned by one flow run, so allow that connection to cross listener
        # threads; writes remain serialized by SQLite's transaction handling.
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def start_run(self, metadata: dict | None = None, run_id: str | None = None) -> str:
        run_id = run_id or f"run_{uuid4().hex}"
        self.connection.execute(
            "INSERT INTO workflow_runs(run_id,status,started_at,metadata_json) VALUES(?,?,?,?)",
            (run_id, "running", _now(), _json(metadata or {})),
        )
        self.connection.commit()
        return run_id

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        self.connection.execute("UPDATE workflow_runs SET status=?, completed_at=? WHERE run_id=?", (status, _now(), run_id))
        self.connection.commit()

    def save_profile(self, profile: dict, profile_version: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO candidate_profiles(profile_version,profile_json,created_at) VALUES(?,?,?)",
            (profile_version, _json(profile), _now()),
        )
        self.connection.commit()

    def save_job(self, job: Any) -> None:
        payload = job.to_dict()
        self.connection.execute(
            "INSERT OR IGNORE INTO jobs(record_id,fingerprint,payload_json,created_at) VALUES(?,?,?,?)",
            (job.record_id, job.fingerprint, _json(payload), _now()),
        )
        self.connection.commit()

    def save_verification(self, result: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO verification_results(record_id,verification_version,payload_json,created_at) VALUES(?,?,?,?)",
            (result.record_id, result.verification_version, _json(result.to_dict()), _now()),
        )
        self.connection.commit()

    def save_match(self, result: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO match_analyses(record_id,matching_version,payload_json,created_at) VALUES(?,?,?,?)",
            (result.record_id, result.matching_version, _json(result.to_dict()), _now()),
        )
        self.connection.commit()

    def save_resume(self, result: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO resume_analyses(record_id,resume_version,payload_json,created_at) VALUES(?,?,?,?)",
            (result.record_id, result.resume_version, _json(result.to_dict()), _now()),
        )
        self.connection.commit()

    def save_ranking(self, run_id: str, result: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO ranking_decisions(run_id,record_id,rank,payload_json,created_at) VALUES(?,?,?,?,?)",
            (run_id, result.record_id, result.rank, _json(asdict(result)), _now()),
        )
        self.connection.commit()

    def save_evaluation(self, result: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO agent_evaluations(output_id,agent_name,evaluator_version,payload_json,created_at) VALUES(?,?,?,?,?)",
            (result.output_id, result.agent_name, result.evaluator_version, _json(result.to_dict()), _now()),
        )
        self.connection.commit()

    def save_memory_event(self, event: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO memory_events(event_id,payload_json,created_at) VALUES(?,?,?)",
            (event.event_id, _json(event.to_dict()), event.created_at),
        )
        self.connection.commit()

    def save_approval(self, request: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO approval_requests(action_id,payload_json,created_at) VALUES(?,?,?)",
            (request.action_id, _json(asdict(request)), _now()),
        )
        self.connection.commit()

    def save_outcome(self, event: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO application_outcomes(event_id,record_id,payload_json,created_at) VALUES(?,?,?,?)",
            (event.event_id, event.record_id, _json(event.to_dict()), event.created_at),
        )
        self.connection.commit()

    def save_human_decision(self, decision: Any) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO human_decisions(decision_id,record_id,decision,actor,note,created_at) VALUES(?,?,?,?,?,?)",
            (decision.decision_id, decision.record_id, decision.decision, decision.actor, decision.note, decision.created_at),
        )
        self.connection.commit()

    def count(self, table: str) -> int:
        allowed = {
            "workflow_runs", "candidate_profiles", "jobs", "verification_results",
            "match_analyses", "resume_analyses", "ranking_decisions", "agent_evaluations",
            "memory_events", "approval_requests", "application_outcomes",
            "human_decisions",
        }
        if table not in allowed:
            raise ValueError("unsupported table")
        return int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def persist_pipeline_result(store: SQLiteStore, run_id: str, result: PipelineResult, profile: dict, profile_version: str = "profile_v1") -> None:
    store.save_profile(profile, profile_version)
    for job in result.jobs:
        store.save_job(job)
    for verification in result.verifications:
        store.save_verification(verification)
    for match in result.matches:
        store.save_match(match)
    for resume in result.resumes:
        store.save_resume(resume)
    for ranking in result.rankings:
        store.save_ranking(run_id, ranking)
    for evaluation in result.evaluations:
        store.save_evaluation(evaluation)
    store.complete_run(run_id)
