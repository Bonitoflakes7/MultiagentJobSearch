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

It can render a local Markdown digest or a self-contained HTML preview. Both are drafts and have no outbound side effects.

## Safety boundary

The dashboard is read-only. It does not submit applications, send emails, or alter memory. Delivery integrations and approval controls remain in Phase 10.

## Phase 9 acceptance tests

- Dashboard stats reflect supplied workflow records.
- Opportunity cards show rank, score, confidence, rationale, concerns, and skill gaps.
- Digest includes the daily action plan.
- Learning signals and outcome metrics are visible.
- Untrusted job text is HTML-escaped.
- Empty states and verification alerts are rendered explicitly.

