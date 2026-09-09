import unittest

from app.crew.agents import (
    CREWAI_AGENTS_AVAILABLE,
    JobEvidencePacket,
    build_agent_plan,
    build_evidence_crew,
    build_specialized_agents,
    evidence_packet_to_text,
)


class CrewAgentTests(unittest.TestCase):
    def test_agent_plan_is_explicitly_non_delegating_and_opt_in(self):
        plan = build_agent_plan()
        self.assertIn("verification", plan.agents)
        self.assertFalse(plan.policy.enabled)
        self.assertFalse(plan.policy.allow_delegation)

    def test_structured_evidence_packet_round_trips_to_canonical_text(self):
        packet = JobEvidencePacket(
            title="Python Backend Intern",
            company="Example Co",
            location="Bangalore",
            posting_date="2026-09-08",
            experience_text="0-1 years",
            skills=["Python", "FastAPI"],
            responsibilities=["Build REST APIs"],
            source_quotes=["Python and FastAPI"],
            confidence=0.9,
        )
        text = evidence_packet_to_text(packet)
        self.assertIn("Title: Python Backend Intern", text)
        self.assertIn("Requirements: Python, FastAPI", text)
        self.assertIn("- Build REST APIs", text)

    def test_agent_definitions_are_constructible_without_running_an_llm(self):
        self.assertIsInstance(CREWAI_AGENTS_AVAILABLE, bool)
        agents = build_specialized_agents()
        if CREWAI_AGENTS_AVAILABLE:
            self.assertEqual(set(agents), {"job_discovery", "verification", "matching", "ranking", "resume", "application_strategist", "evaluator", "report"})
            self.assertFalse(agents["evaluator"].allow_delegation)

    def test_evidence_crew_has_structured_output_without_kickoff(self):
        if not CREWAI_AGENTS_AVAILABLE:
            self.skipTest("CrewAI unavailable")
        crew = build_evidence_crew("Title: Python Intern", source_url="https://example.com/job")
        self.assertEqual(len(crew.tasks), 1)
        self.assertIs(crew.tasks[0].output_pydantic, JobEvidencePacket)


if __name__ == "__main__":
    unittest.main()
