from datetime import date
from pathlib import Path
import tempfile
import unittest

from app.pipeline import run_pipeline
from app.storage import SQLiteStore, persist_pipeline_result
from src.job_search_ai.domain.jobs import JobInput
from src.job_search_ai.domain.matching import load_candidate_profile


class StorageTests(unittest.TestCase):
    def test_pipeline_results_survive_database_reopen(self):
        profile_path = "data/candidate/profile_v1.json"
        profile = load_candidate_profile(profile_path)
        result = run_pipeline((JobInput(
            source_kind="paste",
            source_url="https://jobs.example.com/storage",
            raw_text="""Title: Python Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI
""",
        ),), as_of=date(2026, 9, 9))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "job_search.sqlite3"
            first = SQLiteStore(path)
            run_id = first.start_run({"test": True}, run_id="run_storage")
            persist_pipeline_result(first, run_id, result, profile)
            self.assertEqual(first.count("jobs"), 1)
            self.assertEqual(first.count("workflow_runs"), 1)
            first.close()

            second = SQLiteStore(path)
            try:
                self.assertEqual(second.count("jobs"), 1)
                self.assertEqual(second.count("verification_results"), 1)
                self.assertEqual(second.count("match_analyses"), 1)
                self.assertEqual(second.count("ranking_decisions"), 1)
                self.assertEqual(second.count("agent_evaluations"), 2)
            finally:
                second.close()

    def test_immutable_snapshots_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteStore(Path(directory) / "state.sqlite3")
            job = run_pipeline((JobInput(
                source_kind="paste", source_url="https://jobs.example.com/idempotent",
                raw_text="Title: Python Developer\nCompany: Example\nLocation: Bangalore\nPosted: 2026-09-08\nRequirements: Python",
            ),), as_of=date(2026, 9, 9)).jobs[0]
            store.save_job(job)
            store.save_job(job)
            self.assertEqual(store.count("jobs"), 1)
            store.close()


if __name__ == "__main__":
    unittest.main()
