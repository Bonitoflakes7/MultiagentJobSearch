from datetime import date
import unittest

from src.job_search_ai.domain.jobs import JobInput, normalize_job
from src.job_search_ai.domain.verification import verify_job


class FreshnessWindowTests(unittest.TestCase):
    def make(self, posted: str):
        return normalize_job(JobInput(
            source_kind="paste",
            source_url="https://example.com/job",
            raw_text=f"Title: Python Developer\nCompany: Example\nLocation: Bangalore\nExperience: 0-1 years\nPosted: {posted}\nRequirements: Python",
        ))

    def test_default_window_accepts_seven_days(self):
        result = verify_job(self.make("2026-09-02"), as_of=date(2026, 9, 9))
        self.assertEqual(result.status, "verified")

    def test_default_window_rejects_eight_days(self):
        result = verify_job(self.make("2026-09-01"), as_of=date(2026, 9, 9))
        self.assertEqual(result.status, "rejected")

    def test_relative_posting_date_is_supported(self):
        result = verify_job(self.make("2 days ago"), as_of=date(2026, 9, 9))
        self.assertEqual(result.status, "verified")
