# Phase 14: CrewAI Flow orchestration

## Stages

```text
initialize
  → normalize_stage
  → verify_stage
  → match_stage
  → rank_stage
  → resume_stage
  → evaluation_stage
  → publish_stage
```

Each stage calls a tested domain service. CrewAI controls execution and stage handoffs; the domain services remain responsible for validation, scoring, safety, and governance.

## Persistence

```python
flow = build_flow(job_inputs, database_path="data/job_search.sqlite3")
result = flow.kickoff()
```

## Current limitation

The stages are deterministic and do not yet call LLM-backed agents. Phase 15 will add specialized Crews/agents behind selected stages, starting with discovery and evidence extraction, while retaining deterministic validation after every agent output.

