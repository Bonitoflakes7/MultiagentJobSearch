# Testing strategy

## Phase-completion test format

For each phase we will record:

- test input
- expected behavior
- actual result
- evidence inspected
- defects found
- decision: pass, revise, or blocked

## Test layers

- Unit tests for deterministic parsing, scoring, deduplication, and policy rules.
- Contract tests for every agent's structured output.
- Workflow tests using fake model responses and fake external sources.
- Adversarial tests for prompt injection in job descriptions and resumes.
- Regression tests for previously discovered errors.
- Human review samples for quality dimensions that cannot be fully automated.

## First test pack

The initial fixture set should include:

- a strong match
- a keyword-heavy but poor match
- a job with missing salary and unclear seniority
- a duplicate listing from two sources
- an expired or inaccessible listing
- a suspicious description containing instructions aimed at the agent
- a resume with unsupported claims and ambiguous evidence

