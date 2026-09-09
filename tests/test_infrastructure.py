import os
import unittest

from src.job_search_ai.domain.jobs import JobInput
from src.job_search_ai.infrastructure.actions import ApprovalGate, create_action_request
from src.job_search_ai.infrastructure.config import RuntimeConfig
from src.job_search_ai.infrastructure.integrations import SavedInputAdapter, ingest_from_adapter
from src.job_search_ai.infrastructure.observability import TraceRecorder
from src.job_search_ai.infrastructure.reliability import RetryPolicy, call_with_retry


class InfrastructureTests(unittest.TestCase):
    def test_saved_input_adapter_normalizes_without_network(self):
        adapter = SavedInputAdapter((JobInput(source_kind="url", source_url="https://example.com/jobs/1"),))
        records = ingest_from_adapter(adapter)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "needs_enrichment")

    def test_retry_retries_transient_failures(self):
        state = {"calls": 0}

        def flaky():
            state["calls"] += 1
            if state["calls"] < 3:
                raise TimeoutError("temporary")
            return "ok"

        self.assertEqual(call_with_retry(flaky, RetryPolicy(max_attempts=3)), "ok")
        self.assertEqual(state["calls"], 3)

    def test_approval_and_idempotency_prevent_duplicate_execution(self):
        gate = ApprovalGate()
        gate.prepare(create_action_request("action-1", "send_email", "user@example.com", "body"))
        with self.assertRaises(PermissionError):
            gate.execute("action-1", lambda: "sent")
        gate.approve("action-1")
        self.assertEqual(gate.execute("action-1", lambda: "sent"), "sent")
        with self.assertRaises(RuntimeError):
            gate.execute("action-1", lambda: "sent twice")

    def test_trace_recorder_redacts_sensitive_metadata(self):
        recorder = TraceRecorder()
        event = recorder.record("run-1", "email", "prepared", {"api_key": "secret", "record_id": "job-1"})
        self.assertEqual(event.metadata["api_key"], "[REDACTED]")
        self.assertEqual(event.metadata["record_id"], "job-1")

    def test_config_reads_nonsecret_runtime_values(self):
        old = {key: os.environ.get(key) for key in ("JOB_SEARCH_ENV", "JOB_SEARCH_MAX_RETRIES", "JOB_SEARCH_ALLOWED_ACTIONS")}
        try:
            os.environ["JOB_SEARCH_ENV"] = "test"
            os.environ["JOB_SEARCH_MAX_RETRIES"] = "4"
            os.environ["JOB_SEARCH_ALLOWED_ACTIONS"] = "export_resume,send_email"
            config = RuntimeConfig.from_env()
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(config.environment, "test")
        self.assertEqual(config.max_retries, 4)
        self.assertIn("send_email", config.allowed_actions)


if __name__ == "__main__":
    unittest.main()

