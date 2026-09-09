"""Application service that composes the validated offline domain pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.job_search_ai.domain.governance import AgentEvaluation, evaluate_match_output, evaluate_resume_output
from src.job_search_ai.domain.jobs import JobInput, JobRecord, normalize_job
from src.job_search_ai.domain.matching import MatchAnalysis, load_candidate_profile, match_job
from src.job_search_ai.domain.memory import LearningSnapshot, MemoryLedger
from src.job_search_ai.domain.ranking import DailyActionPlan, RankingDecision, build_daily_plan, rank_jobs
from src.job_search_ai.domain.resume import ResumeAnalysis, analyze_resume
from src.job_search_ai.domain.verification import VerificationResult, verify_job
from src.job_search_ai.presentation.dashboard import DashboardSnapshot, build_dashboard


@dataclass(frozen=True)
class PipelineResult:
    jobs: tuple[JobRecord, ...]
    verifications: tuple[VerificationResult, ...]
    matches: tuple[MatchAnalysis, ...]
    resumes: tuple[ResumeAnalysis, ...]
    rankings: tuple[RankingDecision, ...]
    daily_plan: DailyActionPlan
    evaluations: tuple[AgentEvaluation, ...]
    learning: LearningSnapshot
    dashboard: DashboardSnapshot


def run_pipeline(
    job_inputs: tuple[JobInput, ...],
    *,
    profile_path: str | Path = "data/candidate/profile_v1.json",
    as_of: date | None = None,
    max_daily_actions: int = 5,
) -> PipelineResult:
    """Run the application service without network or outbound side effects."""

    profile = load_candidate_profile(profile_path)
    jobs = tuple(normalize_job(item) for item in job_inputs)
    verifications = tuple(verify_job(job, as_of=as_of) for job in jobs)
    matches = tuple(match_job(job, verification, profile) for job, verification in zip(jobs, verifications))
    resumes = tuple(analyze_resume(job, match, profile) for job, match in zip(jobs, matches))
    rankings = rank_jobs(tuple(zip(jobs, matches, verifications)), as_of=as_of)
    daily_plan = build_daily_plan(rankings, as_of=as_of, max_actions=max_daily_actions)
    evaluations = tuple(
        evaluation
        for job, verification, match, resume in zip(jobs, verifications, matches, resumes)
        for evaluation in (
            evaluate_match_output(match, verification, profile, input_snapshot_id=f"{job.record_id}:match"),
            evaluate_resume_output(resume, input_snapshot_id=f"{job.record_id}:resume"),
        )
    )
    learning = MemoryLedger().derive_snapshot()
    dashboard = build_dashboard(jobs, verifications, matches, rankings, daily_plan, resumes, learning)
    return PipelineResult(jobs, verifications, matches, resumes, rankings, daily_plan, evaluations, learning, dashboard)

