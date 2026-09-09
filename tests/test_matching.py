import json
from datetime import date
from pathlib import Path
import unittest

from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.verification import verify_job


PROFILE_PATH = Path(__file__).parents[1] / "data" / "candidate" / "profile_v1.json"


def make_job(text: str):
    job = normalize_job(JobInput(source_kind="paste", raw_text=text, source_url="https://jobs.example.com/role"))
    return job, verify_job(job, as_of=date(2026, 9, 9))


GOOD_JOB = """Title: Python Backend Developer Intern
Company: Example AI Labs
Location: Bangalore, Karnataka
Experience: 0-1 years
Posted: 2026-09-01
Responsibilities:
- Build REST APIs with Python and FastAPI
- Work with PostgreSQL and Docker
Requirements: Python, FastAPI, PostgreSQL, LangChain, RAG
"""


class MatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_candidate_profile(PROFILE_PATH)

    def test_strong_job_has_evidence_backed_high_score(self):
        job, verification = make_job(GOOD_JOB)
        result = match_job(job, verification, self.profile)

        self.assertGreaterEqual(result.overall_score, 80)
        self.assertIn(result.recommendation, {"apply_priority", "apply_review"})
        self.assertIn("Python", result.matched_skills)
        self.assertTrue(any(d.evidence for d in result.dimensions))

    def test_skill_gaps_are_visible(self):
        job, verification = make_job(GOOD_JOB.replace("LangChain, RAG", "Kubernetes, Java"))
        result = match_job(job, verification, self.profile)

        self.assertIn("Kubernetes", result.missing_skills)
        self.assertIn("Java", result.missing_skills)
        self.assertTrue(any("Skill gap" in evidence for d in result.dimensions for evidence in d.gaps))

    def test_rejected_job_is_blocked(self):
        job, verification = make_job(GOOD_JOB.replace("0-1 years", "5-7 years"))
        result = match_job(job, verification, self.profile)

        self.assertEqual(result.recommendation, "blocked")
        self.assertEqual(result.overall_score, 0.0)
        self.assertTrue(result.hard_constraints)

    def test_unknown_fields_reduce_confidence_and_add_warning(self):
        job, verification = make_job("""Title: Python Developer
Company: Example Co
Location: Bangalore
Requirements: Python
""")
        result = match_job(job, verification, self.profile)

        self.assertLess(result.confidence, 0.8)
        self.assertTrue(result.warnings)

    def test_profile_is_loaded_without_contact_fields(self):
        profile = load_candidate_profile(PROFILE_PATH)
        self.assertNotIn("contact", profile)
        self.assertIn("Python", json.dumps(profile))


if __name__ == "__main__":
    unittest.main()
