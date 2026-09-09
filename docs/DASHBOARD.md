# Phase 9: Dashboard and digest delivery

## Current output

The presentation layer produces:

- dashboard statistics
- ranked opportunity cards
- scores and confidence
- “why this job?” explanations
- concerns and skill gaps
- bounded daily actions
- preference signals
- application/interview/offer metrics
- alerts for uncertain verification and unexplained outcomes
- explicit separation of AI recommendation, human decision, external action, and outcome

It can render a local Markdown digest or a self-contained HTML preview. Both are drafts and have no outbound side effects.

## Safety boundary

The dashboard does not treat an AI recommendation as an application. Human decisions are persisted separately in `human_decisions`. An external application action can only be prepared after explicit human approval, and execution still requires the existing approval gate and idempotency control. Email and application submission remain external actions, never recommendation states.

## Phase 19 interaction states

Each opportunity exposes:

- AI recommendation: apply, review, tailor, monitor, or skip.
- Human decision: approve, reject, interested, not interested, or already applied.
- External action: not requested, prepared, approved, or executed.
- Outcome: unknown, applied, rejected, interview, offer, withdrawn.

## Phase 9 acceptance tests

- Dashboard stats reflect supplied workflow records.
- Opportunity cards show rank, score, confidence, rationale, concerns, and skill gaps.
- Digest includes the daily action plan.
- Learning signals and outcome metrics are visible.
- Untrusted job text is HTML-escaped.
- Empty states and verification alerts are rendered explicitly.
