import tempfile
import unittest
from pathlib import Path

from app.storage import SQLiteStore
from src.job_search_ai.domain.hitl import (
    prepare_application_action,
    record_human_decision,
)


class HumanInLoopTests(unittest.TestCase):
    def test_recommendation_is_not_a_human_decision_or_external_action(self):
        decision = record_human_decision("job-1", "approve_recommendation", decision_id="decision-1")
        self.assertEqual(decision.decision, "approve_recommendation")
        action = prepare_application_action("apply", decision, action_id="action-1", target="job-1", payload="draft")
        self.assertEqual(action.status, "prepared")

    def test_external_action_requires_human_approval(self):
        decision = record_human_decision("job-1", "interested", decision_id="decision-2")
        with self.assertRaises(PermissionError):
            prepare_application_action("apply", decision, action_id="action-2", target="job-1", payload="draft")

    def test_human_decision_is_durable_and_idempotent(self):
        decision = record_human_decision("job-1", "not_interested", decision_id="decision-3")
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteStore(Path(directory) / "state.sqlite3")
            try:
                store.save_human_decision(decision)
                store.save_human_decision(decision)
                self.assertEqual(store.count("human_decisions"), 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
