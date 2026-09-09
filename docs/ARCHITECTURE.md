# System architecture

## Design choice

Use a controlled workflow with specialist agents. Agents produce typed proposals and analyses; orchestration code controls ordering, retries, approval gates, budgets, and termination.

Free-form agent-to-agent conversation is optional and limited to conflict resolution. It is not the system's source of truth.

## High-level flow

```text
Input sources
    |
    v
Ingestion -> Normalization -> Verification -> Candidate matching
                                      |              |
                                      v              v
                                  Job memory      Ranking
                                                     |
                                      +--------------+--------------+
                                      v                             v
                              Resume advisor                  Action plan
                                      |                             |
                                      +--------------+--------------+
                                                     v
                                             Human approval
                                                     |
                                      +--------------+--------------+
                                      v                             v
                              Draft report/email              Application record
                                                                    |
                                                                    v
                                                             Outcome tracking
                                                                    |
                                                                    v
                                                          Evaluation and learning
```

## Application layout

```text
src/job_search_ai/
  agents/              specialist prompts, tools, and result adapters
  orchestration/       workflow, state transitions, retries, gates, budgets
  domain/              typed entities, enums, validation, scoring rules
  infrastructure/      persistence, model clients, source adapters, logging
tests/
  unit/                deterministic domain and validation tests
  contract/            agent input/output schema tests
  workflow/            end-to-end orchestration tests with fake agents
  evaluations/         benchmark cases and policy comparisons
docs/                  roadmap, architecture, contracts, evaluation policy
```

## Source of truth

The database records and immutable run snapshots are authoritative. Prompts, model responses, messages, and evaluator results are evidence attached to records; they are not allowed to silently mutate prior decisions.

## Agent boundaries

- Discovery finds candidates; it does not rank them.
- Verification checks listing quality; it does not infer personal fit.
- Matching explains candidate-job compatibility; it does not decide application order.
- Ranking orders opportunities; it does not rewrite resumes.
- Resume agents may transform existing evidence but cannot create facts.
- Evaluator judges outputs against evidence and rubrics; it does not silently rewrite history.

