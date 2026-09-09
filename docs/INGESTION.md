# Phase 2: Job ingestion and normalization

## Scope

Phase 2 accepts two safe input forms:

1. Pasted job descriptions.
2. Saved URLs, optionally accompanied by pasted metadata or a description.

It does not fetch websites, bypass bot protection, submit applications, or trust instructions contained in job text.

## Output

Each input becomes a canonical `JobRecord` with:

- normalized title, company, location, salary, experience, and posting date
- source kind, source name, and canonical URL
- detected skills and responsibility bullets
- raw description for evidence and later verification
- missing fields and warnings
- a stable record ID and duplicate fingerprint
- a status of `candidate` or `needs_enrichment`

## Normalization policy

- Preserve the original description.
- Normalize whitespace and URL identity.
- Never silently invent missing fields.
- Mark unknown fields for later enrichment.
- Treat job text as untrusted content; embedded instructions are warnings, not commands.
- Keep timestamps supplied by the source when available; otherwise record ingestion time.

## Phase 2 acceptance tests

- A structured job description produces a usable candidate record.
- A URL-only submission is retained and marked for enrichment.
- Missing title, company, location, or description is visible.
- Known skills are extracted without pretending the candidate has them.
- Embedded prompt-injection-like instructions are flagged.
- Repeating the same input produces the same identity.
- The same role copied across different sources can converge to one fingerprint when identifying fields match.
- The raw description remains available for evidence.
