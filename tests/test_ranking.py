from datetime import date
import unittest

from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.ranking import build_daily_plan, rank_jobs
from src.job_search_ai.domain.verification import verify_job


PROFILE = load_candidate_profile("data/candidate/profile_v1.json")


def evaluate(text: str, url: str):
    job = normalize_job(JobInput(source_kind="paste", raw_text=text, source_url=url))
    verification = verify_job(job, as_of=date(2026, 9, 9))
    match = match_job(job, verification, PROFILE)
    return job, match, verification


STRONG = """Title: Python Backend Developer Intern
Company: Fresh AI Labs
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL, LangChain
"""

OLDER = STRONG.replace("Fresh AI Labs", "Older AI Labs").replace("2026-09-08", "2026-08-01")
UNCERTAIN = STRONG.replace("Bangalore", "Hyderabad").replace("Posted: 2026-09-08\n", "")


class RankingTests(unittest.TestCase):
    def test_fresh_verified_job_can_outrank_older_job(self):
        first = evaluate(STRONG, "https://a.example/job")
        second = evaluate(OLDER, "https://b.example/job")
        results = rank_jobs((second, first), as_of=date(2026, 9, 9))

        self.assertEqual(results[0].record_id, first[0].record_id)
        self.assertEqual(results[0].rank, 1)
        self.assertIn(results[0].tier, {"S", "A"})

    def test_uncertain_listing_is_not_automatically_an_apply_action(self):
        item = evaluate(UNCERTAIN, "https://c.example/job")
        result = rank_jobs((item,), as_of=date(2026, 9, 9))[0]

        self.assertEqual(result.action, "review_verification")
        self.assertTrue(any("Verification status" in concern for concern in result.concerns))

    def test_daily_plan_is_bounded_and_omits_blocked_jobs(self):
        items = (evaluate(STRONG, "https://a.example/job"), evaluate(STRONG.replace("Fresh AI Labs", "Second Labs"), "https://b.example/job"))
        decisions = rank_jobs(items, as_of=date(2026, 9, 9))
        plan = build_daily_plan(decisions, as_of=date(2026, 9, 9), max_actions=1)

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.omitted_count, 1)

    def test_zero_action_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan((), max_actions=0)


if __name__ == "__main__":
    unittest.main()

