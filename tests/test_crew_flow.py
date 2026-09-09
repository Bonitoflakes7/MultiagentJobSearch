from datetime import date
from pathlib import Path
import tempfile
import unittest

from app.crew.flow import CREWAI_AVAILABLE, build_flow
from src.job_search_ai.infrastructure.integrations import SourceItem
from app.storage import SQLiteStore
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

    def test_flow_has_all_expected_stage_methods(self):
        flow = build_flow(())
        for name in ("initialize", "agent_preflight", "discovery_stage", "normalize_stage", "verify_stage", "match_stage", "rank_stage", "resume_stage", "evaluation_stage", "publish_stage"):
            self.assertTrue(hasattr(flow, name), name)

    def test_flow_persists_results_when_listeners_use_worker_threads(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "flow.sqlite3"
            flow = build_flow((JobInput(
                source_kind="paste",
                source_url="https://jobs.example.com/crew-flow-storage",
                raw_text="""Title: Python Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI
""",
            ),), as_of=date(2026, 9, 9), database_path=database_path)
            result = flow.kickoff()
            self.assertEqual(len(result.jobs), 1)

            store = SQLiteStore(database_path)
            try:
                self.assertEqual(store.count("workflow_runs"), 1)
                self.assertEqual(store.count("jobs"), 1)
                self.assertEqual(store.count("agent_evaluations"), 2)
            finally:
                store.close()

    def test_flow_accepts_permitted_source_adapter_before_verification(self):
        class FixtureAdapter:
            def fetch(self):
                return (SourceItem(
                    "fixture-1",
                    "fixture_source",
                    JobInput(
                        source_kind="url",
                        source_url="https://fixture.example/jobs/1",
                        raw_text="""Title: AI Engineer Intern
Company: Fixture Labs
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI
""",
                    ),
                ),)

        flow = build_flow((), as_of=date(2026, 9, 9), source_adapters=(FixtureAdapter(),))
        result = flow.kickoff()
        self.assertEqual(len(result.jobs), 1)
        self.assertEqual(result.jobs[0].source_name, "fixture_source")
        self.assertEqual(result.verifications[0].status, "verified")

    def test_availability_is_explicit(self):
        self.assertIsInstance(CREWAI_AVAILABLE, bool)


if __name__ == "__main__":
    unittest.main()
