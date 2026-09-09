# Core data contracts

All agent handoffs must use versioned structured records. Free text may be included for explanation, but required decisions must be represented as fields with validation.

## Required record families

- `CandidateProfile`: identity-independent career facts, preferences, constraints, and evidence.
- `JobRecord`: canonical job information, source metadata, raw description, and freshness state.
- `VerificationResult`: checks performed, evidence, uncertainty, and review status.
- `MatchAnalysis`: dimension scores, supporting evidence, gaps, recommendation, and confidence.
- `RankingDecision`: rank, tier, factors, conflicts, and recommended action.
- `ResumeChangeProposal`: change type, before/after text, evidence references, and fabrication check.
- `EvaluationResult`: rubric scores, defects, severity, feedback, and evaluator version.
- `UserFeedback`: explicit preference signal with timestamp and context.
- `ApplicationOutcome`: application state, result, known reason, and confidence in that reason.

## Required metadata on every agent result

```text
run_id
record_id
agent_name
agent_version
model_identifier
input_snapshot_id
created_at
status
confidence
evidence_references
warnings
```

## Safety states

Every consequential record should support `draft`, `needs_review`, `approved`, `rejected`, and `superseded`. Never overwrite an approved or historical result in place.

