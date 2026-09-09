from datetime import date
import unittest

from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.resume import analyze_resume, validate_tailoring_claims
from src.job_search_ai.domain.verification import verify_job


PROFILE = load_candidate_profile("data/candidate/profile_v1.json")


def evaluate(text: str):
    job = normalize_job(JobInput(source_kind="paste", raw_text=text, source_url="https://jobs.example.com/role"))
    verification = verify_job(job, as_of=date(2026, 9, 9))
    return job, match_job(job, verification, PROFILE)


class ResumeTests(unittest.TestCase):
    def test_supported_skills_become_safe_emphasis_proposals(self):
        job, match = evaluate("""Title: Python Backend Developer
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL, LangChain
""")
        result = analyze_resume(job, match, PROFILE)

        self.assertIn("Python", result.supported_job_skills)
        self.assertFalse(any("Python" in claim for claim in validate_tailoring_claims(result.proposals)))
        self.assertTrue(any(p.change_type == "emphasize_existing_evidence" for p in result.proposals))

    def test_missing_skills_are_blocked_from_claims(self):
        job, match = evaluate("""Title: Python Backend Developer
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, Kubernetes, Java
""")
        result = analyze_resume(job, match, PROFILE)

        self.assertIn("Kubernetes", result.blocked_claims)
        self.assertIn("Java", result.blocked_claims)
        self.assertTrue(validate_tailoring_claims(result.proposals))

    def test_user_supplied_project_requires_confirmation(self):
        job, match = evaluate("""Title: AI Engineer Intern
Company: Health AI Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: FastAPI, LangGraph, Gemini, Tesseract, RAG
""")
        result = analyze_resume(job, match, PROFILE)

        project_proposals = [p for p in result.proposals if "HealthRecord" in p.proposed_change]
        self.assertTrue(project_proposals)
        self.assertTrue(all(p.requires_human_review for p in project_proposals))

    def test_no_automatic_resume_text_is_created(self):
        job, match = evaluate("""Title: Python Developer
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python
""")
        result = analyze_resume(job, match, PROFILE)

        self.assertTrue(result.proposals)
        self.assertFalse(any("invent" in p.proposed_change.casefold() for p in result.proposals))


if __name__ == "__main__":
    unittest.main()

