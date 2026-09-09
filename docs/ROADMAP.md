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

## Phase 3 — verification and safety gates (implemented)

Check URL accessibility, job freshness, duplicate identity, location, seniority, employment type, and suspicious or ambiguous content.

Acceptance: the system can explain why a listing is verified, uncertain, rejected, or needs human review. The offline verifier and duplicate-group detector are implemented in `src/job_search_ai/domain/verification.py`; network-dependent checks remain explicitly unverified.

## Phase 4 — matching and explainable scoring (implemented)

Compare each verified job with the candidate profile. Produce weighted dimensions, evidence, skill gaps, uncertainty, and a recommendation.

Acceptance: scores are reproducible from a stored input snapshot and never depend on hidden conversational history. The baseline matcher is implemented in `src/job_search_ai/domain/matching.py` with weighted dimensions, evidence, gaps, confidence, and recommendation bands.

## Phase 5 — ranking and daily action plan (implemented)

Rank jobs using fit, personal preference, career value, freshness, effort, and application probability. Produce tiers and recommended next actions.

Acceptance: ranking explanations identify the factors that changed an item's position and handle ties or conflicts explicitly. The baseline ranker and bounded action-plan builder are implemented in `src/job_search_ai/domain/ranking.py`.

## Phase 6 — resume analysis and controlled tailoring (implemented)

Suggest job-specific improvements and generate an optional tailored draft. Enforce a no-fabrication policy and preserve the base resume.

Acceptance: every proposed change is classified as reorder, rewrite, clarify, quantify, or unsupported claim; unsupported claims are blocked. The safe baseline analysis is implemented in `src/job_search_ai/domain/resume.py`; automatic resume text generation remains gated behind a confirmed source snapshot and human approval.

## Phase 7 — evaluator and governance layer (implemented)

Score agent outputs against rubrics, detect errors, record feedback, and create versioned improvement proposals.

Acceptance: evaluator decisions are auditable and a new policy cannot replace the current policy without passing regression tests. The evaluator and champion/challenger comparison logic are implemented in `src/job_search_ai/domain/governance.py`.

## Phase 8 — memory and learning from feedback (implemented)

Store user reactions, accepted/rejected recommendations, application outcomes, interview outcomes, and known reasons for failure.

Acceptance: the system learns preference and calibration signals without treating every rejection as proof that the original prediction was wrong. The append-only memory ledger and replayable learning snapshot are implemented in `src/job_search_ai/domain/memory.py`.

## Phase 9 — dashboard and digest delivery (implemented)

Add a dashboard, “why?” views, daily/weekly reports, and draft email notifications.

Acceptance: the user can inspect the evidence behind every recommendation and approve any outbound communication. The read-only dashboard snapshot and Markdown/HTML digest renderers are implemented in `src/job_search_ai/presentation/dashboard.py`; outbound delivery remains Phase 10.

## Phase 10 — integrations and production hardening (baseline implemented)

Add permitted job sources, authentication, retries, idempotency, observability, cost controls, access controls, and deployment documentation.

Acceptance: failures are recoverable, side effects are authorized, secrets are protected, and the system can be demonstrated end to end. The baseline source-adapter, retry, approval, observability, and runtime-configuration boundaries are implemented; durable production deployment remains hardening work.

## Phase 11 — research-grade evaluation (implemented)

Build a historical benchmark and compare policy versions using ranking quality, calibration, user approval, duplicate rate, and application/interview conversion.

Acceptance: improvements are supported by measured results rather than claims from the evaluator alone. Versioned benchmark cases, validation, ranking metrics, calibration metrics, safety indicators, and policy deltas are implemented in `src/job_search_ai/domain/research_eval.py`.

## Phase 12 — application foundation (implemented)

Create the real application package, runtime entry point, dependency configuration, and CrewAI Flow boundary while keeping the validated domain pipeline as the source of truth.

## Phase 13 — database and durable state (implemented)

Persist workflow runs, profile versions, jobs, agent results, evaluations, memory events, approvals, and outcomes in SQLite with immutable versioned snapshots and idempotent retries.

## Phase 14 — CrewAI Flow orchestration (implemented)

Use an explicit CrewAI Flow to orchestrate the validated stages from initialization through publication, with optional SQLite persistence and an offline fallback.

## Phase 15 — specialized CrewAI agents (implemented: guarded foundation)

Define specialized discovery, evidence extraction, match explanation, resume advisory, and evaluation agents behind typed output contracts. Agent delegation is disabled, listing content is explicitly untrusted, and live LLM execution is opt-in. Deterministic normalization, verification, scoring, and governance remain mandatory after agent output.

Acceptance: agent definitions can be constructed without an LLM call; evidence output validates against a strict schema; the Flow records the active agent policy before processing input; and no agent can directly publish an application or override a safety gate. Live source discovery and LLM execution will be enabled incrementally after provider configuration and fixture-based tests.

## Phase 16 — tool layer (implemented: guarded foundation)

Expose narrow, permission-checked tools for candidate/profile reads, job persistence, duplicate detection, source validation, matching, evaluations, feedback, email drafts, and resume drafts. No tool sends email or submits an application.

## Phase 17 — permitted source integrations (implemented: bounded first adapters)

Route manual pasted descriptions, saved URLs, explicitly allowlisted company career pages, and RSS/Atom feeds through source records, then normalization and verification. The first live adapters enforce bounded HTTP access, response limits, retries, attribution, and terms review. API-specific adapters, production rate limits/circuit breakers, and source-by-source legal review remain before enabling additional sources.

## Phase 18 — matching and recommendation response (implemented)

Generate a structured recommendation for each ranked job containing verification, fit score, confidence, tier, action, strengths, gaps, resume-safe recommendations, blocked claims, and ranking reasons. Render it to Markdown/dashboard views without allowing an LLM to invent facts.
