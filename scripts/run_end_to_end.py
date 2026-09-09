"""Run a deterministic offline demonstration of the complete current pipeline."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.job_search_ai.domain.governance import evaluate_match_output, evaluate_resume_output
from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.memory import MemoryLedger
from src.job_search_ai.domain.ranking import build_daily_plan, rank_jobs
from src.job_search_ai.domain.research_eval import BenchmarkCase, BenchmarkDataset, evaluate_benchmark
from src.job_search_ai.domain.resume import analyze_resume
from src.job_search_ai.domain.verification import verify_job
from src.job_search_ai.presentation.dashboard import build_dashboard, render_digest_markdown


AS_OF = date(2026, 9, 9)
PROFILE_PATH = ROOT / "data" / "candidate" / "profile_v1.json"

JOB_INPUTS = (
    JobInput(source_kind="paste", source_url="https://jobs.example.com/strong", raw_text="""Title: Python Backend Developer Intern
Company: Example AI Labs
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Responsibilities:
- Build REST APIs using Python and FastAPI
- Work with PostgreSQL and Docker
Requirements: Python, FastAPI, PostgreSQL, LangChain, RAG
"""),
    JobInput(source_kind="paste", source_url="https://jobs.example.com/review", raw_text="""Title: AI Engineer Intern
Company: Example Health AI
Location: Pune
Experience: 0-1 years
Requirements: Python, FastAPI, LangGraph, Gemini, Kubernetes
"""),
    JobInput(source_kind="paste", source_url="https://jobs.example.com/reject", raw_text="""Title: Senior Backend Engineer
Company: Example Systems
Location: Bangalore
Experience: 5-7 years
Posted: 2026-09-01
Requirements: Python, FastAPI
"""),
)


def main() -> int:
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = tuple(normalize_job(item) for item in JOB_INPUTS)
    verifications = tuple(verify_job(job, as_of=AS_OF) for job in jobs)
    matches = tuple(match_job(job, verification, profile) for job, verification in zip(jobs, verifications))
    resumes = tuple(analyze_resume(job, match, profile) for job, match in zip(jobs, matches))
    ranked = rank_jobs(tuple(zip(jobs, matches, verifications)), as_of=AS_OF)
    plan = build_daily_plan(ranked, as_of=AS_OF, max_actions=3)

    ledger = MemoryLedger()
    ledger.record_preference(event_id="demo-like", record_id=jobs[0].record_id, direction="like", terms=("python", "backend"))
    learning = ledger.derive_snapshot()
    dashboard = build_dashboard(jobs, verifications, matches, ranked, plan, resumes, learning)

    evaluations = [
        evaluate_match_output(match, verification, profile, input_snapshot_id=f"demo-{job.record_id}")
        for job, match, verification in zip(jobs, matches, verifications)
    ]
    evaluations.extend(
        evaluate_resume_output(resume, input_snapshot_id=f"demo-resume-{resume.record_id}")
        for resume in resumes
    )
    benchmark = BenchmarkDataset(
        dataset_version="demo-v1",
        cases=tuple(BenchmarkCase(
            case_id=f"demo-{index}",
            job_id=job.record_id,
            policy_id="baseline-v1",
            predicted_score=match.overall_score,
            rank=next(item.rank for item in ranked if item.record_id == job.record_id),
            recommendation=match.recommendation,
            useful_outcome=(index == 1),
        ) for index, (job, match) in enumerate(zip(jobs, matches), start=1)),
        description="Deterministic smoke-test benchmark",
    )
    research_report = evaluate_benchmark(benchmark, top_k=2)

    result = {
        "jobs": [{"id": job.record_id, "title": job.title, "posted": job.posting_date, "verification": verification.status} for job, verification in zip(jobs, verifications)],
        "matches": [{"id": match.record_id, "score": match.overall_score, "recommendation": match.recommendation} for match in matches],
        "ranked": [{"rank": item.rank, "tier": item.tier, "id": item.record_id, "action": item.action} for item in ranked],
        "daily_actions": [{"order": action.order, "action": action.action, "id": action.record_id} for action in plan.actions],
        "governance_passed": sum(1 for item in evaluations if item.passed),
        "governance_total": len(evaluations),
        "research_metrics": research_report.metrics,
        "digest_preview": render_digest_markdown(dashboard).splitlines()[:12],
    }
    print(json.dumps(result, indent=2))
    return 0 if all(item.passed for item in evaluations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
