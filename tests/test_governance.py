from datetime import date
from dataclasses import replace
import unittest

from src.job_search_ai.domain.governance import (
    PolicyMetrics,
    compare_policy_versions,
    evaluate_match_output,
    evaluate_resume_output,
)
from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.matching import load_candidate_profile, match_job
from src.job_search_ai.domain.resume import analyze_resume
from src.job_search_ai.domain.verification import verify_job


PROFILE = load_candidate_profile("data/candidate/profile_v1.json")


def evaluated_match(text: str):
    job = normalize_job(JobInput(source_kind="paste", raw_text=text, source_url="https://jobs.example.com/role"))
    verification = verify_job(job, as_of=date(2026, 9, 9))
    match = match_job(job, verification, PROFILE)
    return job, verification, match


GOOD = """Title: Python Backend Developer Intern
Company: Example Co
Location: Bangalore
Experience: 0-1 years
Posted: 2026-09-08
Requirements: Python, FastAPI, PostgreSQL
"""


class GovernanceTests(unittest.TestCase):
    def test_good_match_passes_evaluation(self):
        job, verification, match = evaluated_match(GOOD)
        result = evaluate_match_output(match, verification, PROFILE, input_snapshot_id="snapshot-1")

        self.assertTrue(result.passed)
        self.assertEqual(result.agent_name, "matching")
        self.assertIn("evidence_grounding", result.rubric_scores)

    def test_unsupported_match_evidence_fails_evaluation(self):
        job, verification, match = evaluated_match(GOOD)
        bad_match = replace(match, matched_skills=("Kubernetes",))
        result = evaluate_match_output(bad_match, verification, PROFILE, input_snapshot_id="snapshot-2")

        self.assertFalse(result.passed)
        self.assertTrue(any(f.code == "unsupported_match_evidence" for f in result.findings))

    def test_resume_output_is_evaluated_for_safety(self):
        job, verification, match = evaluated_match(GOOD)
        resume = analyze_resume(job, match, PROFILE)
        result = evaluate_resume_output(resume, input_snapshot_id="snapshot-3")

        self.assertTrue(result.passed)
        self.assertIn("safety", result.rubric_scores)

    def test_policy_comparison_retains_champion_on_safety_regression(self):
        champion = PolicyMetrics("ranking-v1", 100, 0.70, 0.02, 0.01, 0.60)
        challenger = PolicyMetrics("ranking-v2", 100, 0.75, 0.04, 0.01, 0.65)
        result = compare_policy_versions(champion, challenger)

        self.assertEqual(result.decision, "retain_champion")
        self.assertIn("Safety error rate regressed", " ".join(result.reasons))

    def test_policy_comparison_promotes_only_a_better_safe_challenger(self):
        champion = PolicyMetrics("ranking-v1", 100, 0.70, 0.02, 0.01, 0.60)
        challenger = PolicyMetrics("ranking-v2", 100, 0.74, 0.01, 0.00, 0.66)
        result = compare_policy_versions(champion, challenger)

        self.assertEqual(result.decision, "promote_challenger")


if __name__ == "__main__":
    unittest.main()
