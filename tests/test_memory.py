from pathlib import Path
import tempfile
import unittest

from src.job_search_ai.domain.memory import MemoryLedger


class MemoryTests(unittest.TestCase):
    def test_explicit_preferences_create_signals(self):
        ledger = MemoryLedger()
        ledger.record_preference(event_id="f1", record_id="job-1", direction="like", terms=("python", "backend"))
        ledger.record_preference(event_id="f2", record_id="job-2", direction="like", terms=("python",))
        ledger.record_preference(event_id="f3", record_id="job-3", direction="dislike", terms=("frontend",))
        snapshot = ledger.derive_snapshot()

        by_term = {signal.term: signal for signal in snapshot.preference_signals}
        self.assertEqual(by_term["python"].direction, "like")
        self.assertEqual(by_term["frontend"].direction, "dislike")
        self.assertEqual(by_term["python"].evidence_count, 2)

    def test_rejections_do_not_create_preference_signals(self):
        ledger = MemoryLedger()
        ledger.record_outcome(event_id="o1", record_id="job-1", outcome="rejected", recommendation="apply_priority")
        snapshot = ledger.derive_snapshot()

        self.assertEqual(snapshot.preference_signals, ())
        self.assertEqual(snapshot.unexplained_outcomes, 1)

    def test_outcomes_are_measured_separately_by_recommendation(self):
        ledger = MemoryLedger()
        ledger.record_outcome(event_id="o1", record_id="job-1", outcome="interview", recommendation="apply_priority")
        ledger.record_outcome(event_id="o2", record_id="job-2", outcome="rejected", recommendation="apply_priority", reason="role closed", reason_confidence=1.0)
        snapshot = ledger.derive_snapshot()

        metric = snapshot.outcome_metrics[0]
        self.assertEqual(metric.recommendation, "apply_priority")
        self.assertEqual(metric.interview_rate, 0.5)
        self.assertEqual(metric.offer_rate, 0.0)
        self.assertEqual(snapshot.unexplained_outcomes, 0)

    def test_duplicate_event_ids_are_idempotent(self):
        ledger = MemoryLedger()
        self.assertTrue(ledger.record_preference(event_id="same", record_id="job-1", direction="like", terms=("python",)))
        self.assertFalse(ledger.record_preference(event_id="same", record_id="job-1", direction="like", terms=("python",)))
        self.assertEqual(len(ledger.events), 1)

    def test_jsonl_persistence_is_replayable(self):
        ledger = MemoryLedger()
        ledger.record_preference(event_id="f1", record_id="job-1", direction="like", terms=("backend",), created_at="2026-09-09T00:00:00+00:00")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            ledger.save_jsonl(path)
            restored = MemoryLedger.load_jsonl(path)

        self.assertEqual(restored.events, ledger.events)
        self.assertEqual(restored.derive_snapshot().preference_signals[0].term, "backend")


if __name__ == "__main__":
    unittest.main()

