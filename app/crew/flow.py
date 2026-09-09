"""CrewAI Flow orchestration for the validated job-search pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
from uuid import uuid4

from src.job_search_ai.domain.governance import AgentEvaluation, evaluate_match_output, evaluate_resume_output
from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.memory import MemoryLedger
from src.job_search_ai.domain.ranking import build_daily_plan, rank_jobs
from src.job_search_ai.domain.resume import analyze_resume
from src.job_search_ai.domain.verification import verify_job
from src.job_search_ai.presentation.dashboard import build_dashboard

from ..pipeline import PipelineResult
from ..storage import SQLiteStore, persist_pipeline_result


_project_root = Path(__file__).resolve().parents[2]
_crewai_storage = _project_root / "data" / "crewai"
_crewai_local_app_data = _project_root / "data" / "crewai-localappdata"
_crewai_storage.mkdir(parents=True, exist_ok=True)
_crewai_local_app_data.mkdir(parents=True, exist_ok=True)
os.environ["CREWAI_STORAGE_DIR"] = str(_crewai_storage)
os.environ["LOCALAPPDATA"] = str(_crewai_local_app_data)
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

try:
    from crewai.flow.flow import Flow, listen, start
    CREWAI_AVAILABLE = True
except Exception:  # pragma: no cover - fallback for incomplete installations.
    Flow = object  # type: ignore[misc,assignment]
    CREWAI_AVAILABLE = False

    def start(function):
        return function

    def listen(function):
        return function


@dataclass
class JobSearchFlowState:
    job_inputs: tuple[JobInput, ...] = ()
    profile_path: str = "data/candidate/profile_v1.json"
    as_of: date | None = None
    database_path: str | None = None
    run_id: str | None = None
    result: PipelineResult | None = None


class _StagedPipeline:
    """Shared stage implementations used by CrewAI and the offline fallback."""

    def _prepare_runtime(self, inputs: dict) -> None:
        self._input_state = inputs
        self._runtime = {"profile": load_candidate_profile(inputs["profile_path"])}
        self._store = SQLiteStore(inputs["database_path"]) if inputs.get("database_path") else None
        self._run_id = inputs.get("run_id") or f"run_{uuid4().hex}"
        if self._store:
            self._run_id = self._store.start_run({"orchestrator": "crewai_flow"}, run_id=self._run_id)

    def _normalize(self):
        self._runtime["jobs"] = tuple(normalize_job(item) for item in self._input_state["job_inputs"])
        return self._runtime["jobs"]

    def _verify(self):
        self._runtime["verifications"] = tuple(verify_job(job, as_of=self._input_state.get("as_of")) for job in self._runtime["jobs"])
        return self._runtime["verifications"]

    def _match(self):
        self._runtime["matches"] = tuple(match_job(job, verification, self._runtime["profile"]) for job, verification in zip(self._runtime["jobs"], self._runtime["verifications"]))
        return self._runtime["matches"]

    def _rank(self):
        self._runtime["rankings"] = rank_jobs(tuple(zip(self._runtime["jobs"], self._runtime["matches"], self._runtime["verifications"])), as_of=self._input_state.get("as_of"))
        self._runtime["daily_plan"] = build_daily_plan(self._runtime["rankings"], as_of=self._input_state.get("as_of"), max_actions=5)
        return self._runtime["rankings"]

    def _resume(self):
        self._runtime["resumes"] = tuple(analyze_resume(job, match, self._runtime["profile"]) for job, match in zip(self._runtime["jobs"], self._runtime["matches"]))
        return self._runtime["resumes"]

    def _evaluate(self):
        evaluations: list[AgentEvaluation] = []
        for job, verification, match, resume in zip(self._runtime["jobs"], self._runtime["verifications"], self._runtime["matches"], self._runtime["resumes"]):
            evaluations.append(evaluate_match_output(match, verification, self._runtime["profile"], input_snapshot_id=f"{job.record_id}:match"))
            evaluations.append(evaluate_resume_output(resume, input_snapshot_id=f"{job.record_id}:resume"))
        self._runtime["evaluations"] = tuple(evaluations)
        return self._runtime["evaluations"]

    def _publish(self) -> PipelineResult:
        learning = MemoryLedger().derive_snapshot()
        dashboard = build_dashboard(self._runtime["jobs"], self._runtime["verifications"], self._runtime["matches"], self._runtime["rankings"], self._runtime["daily_plan"], self._runtime["resumes"], learning)
        result = PipelineResult(
            jobs=self._runtime["jobs"], verifications=self._runtime["verifications"], matches=self._runtime["matches"], resumes=self._runtime["resumes"], rankings=self._runtime["rankings"], daily_plan=self._runtime["daily_plan"], evaluations=self._runtime["evaluations"], learning=learning, dashboard=dashboard,
        )
        if self._store:
            persist_pipeline_result(self._store, self._run_id, result, self._runtime["profile"])
            self._store.close()
        self._runtime["result"] = result
        return result


if CREWAI_AVAILABLE:
    class JobSearchFlow(Flow, _StagedPipeline):
        """Explicit sequential Flow with inspectable stage boundaries."""

        def __init__(self, input_state: dict | None = None):
            super().__init__()
            self._prepare_runtime(input_state or {})

        @start()
        def initialize(self):
            return "initialized"

        @listen(initialize)
        def normalize_stage(self, _signal):
            return self._normalize()

        @listen(normalize_stage)
        def verify_stage(self, _jobs):
            return self._verify()

        @listen(verify_stage)
        def match_stage(self, _verifications):
            return self._match()

        @listen(match_stage)
        def rank_stage(self, _matches):
            return self._rank()

        @listen(rank_stage)
        def resume_stage(self, _rankings):
            return self._resume()

        @listen(resume_stage)
        def evaluation_stage(self, _resumes):
            return self._evaluate()

        @listen(evaluation_stage)
        def publish_stage(self, _evaluations):
            return self._publish()
else:
    class JobSearchFlow(_StagedPipeline):
        """Offline fallback with the same staged behavior."""

        def __init__(self, state: JobSearchFlowState | None = None):
            state = state or JobSearchFlowState()
            self._prepare_runtime({"job_inputs": state.job_inputs, "profile_path": state.profile_path, "as_of": state.as_of, "database_path": state.database_path, "run_id": state.run_id})

        def kickoff(self) -> PipelineResult:
            self._normalize()
            self._verify()
            self._match()
            self._rank()
            self._resume()
            self._evaluate()
            return self._publish()


def build_flow(job_inputs: tuple[JobInput, ...], *, as_of: date | None = None, profile_path: str | Path = "data/candidate/profile_v1.json", database_path: str | Path | None = None, run_id: str | None = None) -> JobSearchFlow:
    inputs = {"job_inputs": job_inputs, "profile_path": str(profile_path), "as_of": as_of, "database_path": str(database_path) if database_path else None, "run_id": run_id}
    if CREWAI_AVAILABLE:
        return JobSearchFlow(input_state=inputs)
    return JobSearchFlow(state=JobSearchFlowState(**inputs))

