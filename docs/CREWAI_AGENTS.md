# Phase 15: Specialized CrewAI Agents

Phase 15 adds specialized CrewAI agent definitions without giving agents control of safety-critical decisions.

## Agent responsibilities

| Agent | Responsibility | Cannot do |
|---|---|---|
| Job Discovery Researcher | Propose candidate listings and preserve source URLs | Verify a listing or send applications |
| Verification Agent | Validate completeness, freshness, duplicates, suspicious text, location, and experience | Override a safety gate |
| Matching Agent | Explain strengths, gaps, and confidence against candidate evidence | Invent experience or change the score policy |
| Ranking Agent | Create S/A/B/C/D tiers and a bounded daily plan | Rank unverified jobs |
| Resume Agent | Suggest evidence-backed emphasis, ordering, and wording | Invent skills, metrics, or experience |
| Application Strategist Agent | Recommend apply/review/monitor, effort, referrals, and tailoring | Send messages or apply automatically |
| Evaluator Agent | Audit every output for evidence, contradictions, unsafe claims, and policy regressions | Approve its own output as final truth |
| Report Agent | Create dashboard data, digests, resume summaries, and explanations | Introduce new claims while formatting |

## Safety boundary

Agent output is a proposal. The Flow sends it through typed parsing, deterministic normalization, freshness/location/experience checks, matching, and governance evaluation. The agent policy defaults to disabled live execution; set `JOB_SEARCH_ENABLE_LLM_AGENTS=1` only after configuring a supported LLM provider and testing with fixtures.

The current release constructs and tests the agents but does not call an LLM during normal smoke tests. This keeps development reproducible and prevents an unconfigured provider from making network calls or spending tokens.

## Tool permissions

Agents receive only the tools required for their role through `app/crew/tools.py`. Discovery can save job records and check duplicates; matching can read candidate evidence and calculate a score; resume and strategy agents can create drafts. Draft creation is not sending, and no agent has an application-submission tool.

The Flow currently connects discovery to the local permitted-input adapter for pasted listings and saved URLs. Every resulting record still passes normalization and the Verification Agent’s deterministic seven-day freshness, source, duplicate, safety, location, and experience gates.

## Structured evidence contract

`JobEvidencePacket` requires bounded fields for extracted identity, skills, responsibilities, source quotes, missing fields, safety flags, and confidence. The packet can be converted into canonical job text, after which existing normalization and verification remain authoritative. In the current roster, evidence extraction is a responsibility of the Verification Agent rather than a separate decision-making agent.

## Next increment

Phase 15 will next add a provider adapter and fixture-backed execution test for the evidence extractor, followed by discovery-source adapters. Only after those tests pass should match explanations and resume advice be enabled in production runs.
