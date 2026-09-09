from datetime import date
import unittest

from app.crew.flow import CREWAI_AVAILABLE, build_flow
from src.job_search_ai.domain.jobs import JobInput


class CrewFlowTests(unittest.TestCase):
    def test_flow_boundary_runs_the_validated_pipeline(self):
        flow = build_flow((JobInput(
            source_kind="paste",
            source_url="https://jobs.example.com/crew-flow",
            raw_text="""Title: Python Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI
""",
        ),), as_of=date(2026, 9, 9))
        result = flow.kickoff() if hasattr(flow, "kickoff") else flow.run_pipeline_stage()

        self.assertEqual(result.verifications[0].status, "verified")
        self.assertTrue(result.evaluations)
        self.assertTrue(all(item.passed for item in result.evaluations))

    def test_availability_is_explicit(self):
        self.assertIsInstance(CREWAI_AVAILABLE, bool)


if __name__ == "__main__":
    unittest.main()

