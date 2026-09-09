"""Command-line entry point for the application foundation."""

from __future__ import annotations

import argparse
from datetime import date
import json

from src.job_search_ai.domain.jobs import JobInput

from .pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Job Search Intelligence System")
    parser.add_argument("--smoke", action="store_true", help="run the offline application smoke case")
    args = parser.parse_args()
    if not args.smoke:
        parser.error("the application foundation currently supports --smoke only")
    inputs = (
        JobInput(source_kind="paste", source_url="https://jobs.example.com/strong", raw_text="""Title: Python Backend Developer Intern
Company: Example AI Labs
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL, LangChain
"""),
    )
    result = run_pipeline(inputs, as_of=date(2026, 9, 9))
    print(json.dumps({
        "status": "ok" if all(item.passed for item in result.evaluations) else "failed",
        "jobs": len(result.jobs),
        "verified": sum(item.status == "verified" for item in result.verifications),
        "top_rank": result.rankings[0].record_id if result.rankings else None,
        "daily_actions": len(result.daily_plan.actions),
        "governance_passed": sum(item.passed for item in result.evaluations),
        "governance_total": len(result.evaluations),
    }, indent=2))
    return 0 if all(item.passed for item in result.evaluations) else 1


if __name__ == "__main__":
    raise SystemExit(main())

