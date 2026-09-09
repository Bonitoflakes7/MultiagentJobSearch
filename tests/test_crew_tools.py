from pathlib import Path
import tempfile
import unittest

from app.crew.tools import (
    AgentToolContext,
    ToolPermissionError,
    create_email_draft,
    default_permissions,
    verify_source_url,
)


class CrewToolTests(unittest.TestCase):
    def test_permissions_are_agent_specific(self):
        discovery = AgentToolContext("job_discovery", default_permissions("job_discovery"))
        self.assertTrue(verify_source_url(discovery, "https://example.com/jobs/1"))
        with self.assertRaises(ToolPermissionError):
            create_email_draft(discovery, "Subject", "Body")

    def test_drafts_are_not_send_actions(self):
        strategist = AgentToolContext("application_strategist", default_permissions("application_strategist"))
        draft = create_email_draft(strategist, "Review this role", "Please review", "candidate@example.com")
        self.assertEqual(draft["status"], "draft")
        self.assertNotIn("send", draft)


if __name__ == "__main__":
    unittest.main()
