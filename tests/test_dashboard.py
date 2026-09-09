from datetime import date
import unittest

from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.memory import MemoryLedger
from src.job_search_ai.domain.ranking import build_daily_plan, rank_jobs
from src.job_search_ai.domain.verification import verify_job
from src.job_search_ai.presentation.dashboard import build_dashboard, render_dashboard_html, render_digest_markdown, render_recommendation_markdown


PROFILE = load_candidate_profile("data/candidate/profile_v1.json")
TEXT = """Title: Python Backend Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL
"""


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.job = normalize_job(JobInput(source_kind="paste", raw_text=TEXT, source_url="https://jobs.example.com/1"))
        self.verification = verify_job(self.job, as_of=date(2026, 9, 9))
        self.match = match_job(self.job, self.verification, PROFILE)
        self.decision = rank_jobs(((self.job, self.match, self.verification),), as_of=date(2026, 9, 9))
        self.plan = build_daily_plan(self.decision, as_of=date(2026, 9, 9))

    def test_dashboard_contains_stats_and_opportunity_card(self):
        ledger = MemoryLedger()
        ledger.record_outcome(event_id="o1", record_id=self.job.record_id, outcome="interview", recommendation="apply_priority")
        snapshot = build_dashboard((self.job,), (self.verification,), (self.match,), self.decision, self.plan, learning=ledger.derive_snapshot())

        self.assertEqual(snapshot.stats["jobs_discovered"], 1)
        self.assertEqual(snapshot.stats["interviews"], 1)
        self.assertEqual(snapshot.top_opportunities[0].title, "Python Backend Developer Intern")
        self.assertEqual(snapshot.top_opportunities[0].posting_date, "2026-09-08")

    def test_markdown_digest_contains_explanation_and_action(self):
        snapshot = build_dashboard((self.job,), (self.verification,), (self.match,), self.decision, self.plan)
        digest = render_digest_markdown(snapshot)

        self.assertIn("Top opportunities", digest)
        self.assertIn("Python Backend Developer Intern", digest)
        self.assertIn("Today's action plan", digest)

    def test_structured_recommendation_contains_score_gaps_resume_guards_and_rank_reason(self):
        snapshot = build_dashboard(
            (self.job,), (self.verification,), (self.match,), self.decision, self.plan,
            resume_analyses=(),
        )
        recommendation = snapshot.recommendations[0]
        rendered = render_recommendation_markdown(recommendation)
        self.assertIn("Verification: Verified", rendered)
        self.assertIn("Fit score:", rendered)
        self.assertIn("Confidence:", rendered)
        self.assertIn("Tier:", rendered)
        self.assertIn("Why rank?", rendered)
        self.assertIn("Resume recommendations", rendered)

    def test_html_renderer_escapes_untrusted_job_text(self):
        hostile = normalize_job(JobInput(source_kind="paste", raw_text=TEXT.replace("Example Co", "<script>alert(1)</script>"), source_url="https://jobs.example.com/2"))
        verification = verify_job(hostile, as_of=date(2026, 9, 9))
        match = match_job(hostile, verification, PROFILE)
        decisions = rank_jobs(((hostile, match, verification),), as_of=date(2026, 9, 9))
        plan = build_daily_plan(decisions)
        snapshot = build_dashboard((hostile,), (verification,), (match,), decisions, plan)
        html = render_dashboard_html(snapshot)

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
