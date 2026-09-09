# Delivery roadmap

Each phase ends with a demonstrable test session and a written evaluation. A phase is not complete because the code runs; it is complete when its acceptance checks pass and its failure modes are understood.

## Phase 0 — foundation and contracts

Define the product boundary, repository structure, domain records, agent contracts, safety rules, evaluation policy, and test strategy.

Acceptance: a new contributor can understand where each capability belongs and how an agent result will be tested.

## Phase 1 — candidate profile and evidence

Import a resume and manually supplied preferences. Extract skills, projects, experience, education, constraints, goals, and evidence references.

Acceptance: every candidate claim has provenance, confidence, and a distinction between proven, inferred, desired, and unknown.

## Phase 2 — job ingestion and normalization (implemented)

Accept saved job URLs, pasted descriptions, and permitted source data. Normalize them into a canonical job record.

Acceptance: malformed, incomplete, duplicate, and stale-looking records are identified without silently disappearing. The deterministic first version is implemented in `src/job_search_ai/domain/jobs.py`; website fetching and source adapters remain future work.

## Phase 3 — verification and safety gates

Check URL accessibility, job freshness, duplicate identity, location, seniority, employment type, and suspicious or ambiguous content.

Acceptance: the system can explain why a listing is verified, uncertain, rejected, or needs human review.

## Phase 4 — matching and explainable scoring

Compare each verified job with the candidate profile. Produce weighted dimensions, evidence, skill gaps, uncertainty, and a recommendation.

Acceptance: scores are reproducible from a stored input snapshot and never depend on hidden conversational history.

## Phase 5 — ranking and daily action plan

Rank jobs using fit, personal preference, career value, freshness, effort, and application probability. Produce tiers and recommended next actions.

Acceptance: ranking explanations identify the factors that changed an item's position and handle ties or conflicts explicitly.

## Phase 6 — resume analysis and controlled tailoring

Suggest job-specific improvements and generate an optional tailored draft. Enforce a no-fabrication policy and preserve the base resume.

Acceptance: every proposed change is classified as reorder, rewrite, clarify, quantify, or unsupported claim; unsupported claims are blocked.

## Phase 7 — evaluator and governance layer

Score agent outputs against rubrics, detect errors, record feedback, and create versioned improvement proposals.

Acceptance: evaluator decisions are auditable and a new policy cannot replace the current policy without passing regression tests.

## Phase 8 — memory and learning from feedback

Store user reactions, accepted/rejected recommendations, application outcomes, interview outcomes, and known reasons for failure.

Acceptance: the system learns preference and calibration signals without treating every rejection as proof that the original prediction was wrong.

## Phase 9 — dashboard and digest delivery

Add a dashboard, “why?” views, daily/weekly reports, and draft email notifications.

Acceptance: the user can inspect the evidence behind every recommendation and approve any outbound communication.

## Phase 10 — integrations and production hardening

Add permitted job sources, authentication, retries, idempotency, observability, cost controls, access controls, and deployment documentation.

Acceptance: failures are recoverable, side effects are authorized, secrets are protected, and the system can be demonstrated end to end.

## Phase 11 — research-grade evaluation

Build a historical benchmark and compare policy versions using ranking quality, calibration, user approval, duplicate rate, and application/interview conversion.

Acceptance: improvements are supported by measured results rather than claims from the evaluator alone.
