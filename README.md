# Job Search Intelligence System

A human-in-the-loop, evidence-backed multi-agent system for discovering jobs, verifying listings, evaluating candidate fit, prioritizing applications, improving resumes, and learning from real application outcomes.

## Product principle

The system is a decision-support product, not an autonomous application bot. It may recommend and prepare actions, but the user approves consequential actions such as sending email or applying.

## Current status

Phase 0 — architecture and testing foundation.

No external job-site integrations or automatic applications are enabled yet.

## Planned stack

- Python application
- CrewAI Flows as the initial orchestration layer
- Typed domain records and versioned agent outputs
- Relational persistence for jobs, candidate evidence, evaluations, feedback, and outcomes
- Web dashboard and digest generation after the core workflow is reliable

See [docs/ROADMAP.md](docs/ROADMAP.md) for phases and acceptance criteria.

