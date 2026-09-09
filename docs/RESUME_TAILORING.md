# Phase 6: Resume analysis and controlled tailoring

## Current behavior

The system produces a tailoring plan rather than silently rewriting the resume. Each proposal is classified as:

- `emphasize_existing_evidence`
- `reorder_existing_evidence`
- `clarify_existing_evidence`
- `add_verified_evidence`
- `unsupported_claim_blocked`

## No-fabrication policy

Automatic tailoring cannot invent or imply:

- skills
- projects
- employers
- responsibilities
- metrics
- certifications
- production experience

Missing job skills become visible gaps and are explicitly blocked from being added as existing experience.

## Evidence boundary

Projects marked `verified_resume` may be emphasized or reordered. Projects marked `verified_user`, such as HealthRecord AI in the current profile, may inform analysis but require human confirmation before being added to a resume draft.

## Phase 6 acceptance tests

- Existing skills produce safe emphasis proposals.
- Missing skills produce blocked claims.
- User-supplied projects require confirmation.
- Proposals retain evidence references.
- No automatic resume text is generated without an approved source snapshot and human review.

