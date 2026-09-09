from datetime import date
import unittest

from app.pipeline import run_pipeline
from src.job_search_ai.domain.jobs import JobInput


class AppPipelineTests(unittest.TestCase):
    def test_application_service_composes_validated_pipeline(self):
        result = run_pipeline((JobInput(
            source_kind="paste",
            source_url="https://jobs.example.com/app-test",
            raw_text="""Title: Python Backend Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL
""",
        ),), as_of=date(2026, 9, 9))

        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.verifications[0].status, "verified")
        self.assertTrue(result.rankings)
        self.assertEqual(len(result.evaluations), 2)
        self.assertTrue(all(item.passed for item in result.evaluations))
        self.assertEqual(result.dashboard.stats["jobs_discovered"], 1)


if __name__ == "__main__":
    unittest.main()

