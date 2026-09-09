"""Optional CrewAI Flow adapter around the validated application service.

The module remains importable when CrewAI is not installed, so the offline
pipeline and its tests remain usable during dependency setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path

from src.job_search_ai.domain.jobs import JobInput

from ..pipeline import PipelineResult, run_pipeline

_project_root = Path(__file__).resolve().parents[2]
_crewai_storage = _project_root / "data" / "crewai"
_crewai_local_app_data = _project_root / "data" / "crewai-localappdata"
_crewai_storage.mkdir(parents=True, exist_ok=True)
_crewai_local_app_data.mkdir(parents=True, exist_ok=True)
# Keep CrewAI's local telemetry/credential files inside the project workspace
# for this application. This avoids relying on platform user-data locations
# that may be unavailable in managed environments.
os.environ["CREWAI_STORAGE_DIR"] = str(_crewai_storage)
os.environ["LOCALAPPDATA"] = str(_crewai_local_app_data)

try:  # CrewAI is optional until its full dependency set is installed.
    from crewai.flow.flow import Flow, start
    CREWAI_AVAILABLE = True
except Exception:  # pragma: no cover - also covers incomplete optional installs.
    Flow = object  # type: ignore[misc,assignment]
    CREWAI_AVAILABLE = False

    def start(function):
        return function


@dataclass
class JobSearchFlowState:
    job_inputs: tuple[JobInput, ...] = ()
    profile_path: str = "data/candidate/profile_v1.json"
    as_of: date | None = None
    result: PipelineResult | None = None


if CREWAI_AVAILABLE:
    class JobSearchFlow(Flow):
        """First Flow boundary; domain services remain the source of truth."""

        def __init__(self, input_state: dict | None = None):
            super().__init__()
            self.input_state = input_state or {}

        @start()
        def run_pipeline_stage(self) -> PipelineResult:
            result = run_pipeline(
                tuple(self.input_state["job_inputs"]),
                profile_path=self.input_state["profile_path"],
                as_of=self.input_state.get("as_of"),
            )
            self.state["result"] = result
            return result
else:
    class JobSearchFlow:
        """Offline-compatible fallback with the same public kickoff behavior."""

        def __init__(self, state: JobSearchFlowState | None = None):
            self.state = state or JobSearchFlowState()

        def kickoff(self) -> PipelineResult:
            self.state.result = run_pipeline(
                self.state.job_inputs,
                profile_path=self.state.profile_path,
                as_of=self.state.as_of,
            )
            return self.state.result


def build_flow(job_inputs: tuple[JobInput, ...], *, as_of: date | None = None, profile_path: str | Path = "data/candidate/profile_v1.json") -> JobSearchFlow:
    state = JobSearchFlowState(job_inputs=job_inputs, profile_path=str(profile_path), as_of=as_of)
    if CREWAI_AVAILABLE:
        return JobSearchFlow(input_state={"job_inputs": job_inputs, "profile_path": str(profile_path), "as_of": as_of})
    return JobSearchFlow(state=state)
