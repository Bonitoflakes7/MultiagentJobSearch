# Phase 10: Integrations and production hardening

## Implemented boundaries

- `JobSourceAdapter`: typed contract for permitted job sources.
- `SavedInputAdapter`: offline adapter for pasted descriptions and saved URLs.
- Retry policy: retries only configured transient exceptions with bounded attempts.
- Idempotency ledger: prevents duplicate operations.
- Approval gate: consequential actions require explicit approval before execution.
- Trace recorder: captures workflow events while redacting secret-like metadata.
- Runtime configuration: reads non-secret operational settings from environment variables.

## Action safety

The action gate supports prepared, approved, and executed states. It refuses unapproved execution and rejects duplicate execution keys. Email sending and application submission are not connected yet.

## Source safety

External source adapters must be explicitly permitted, respect source terms and rate limits, and return structured source items. They must not bypass authentication, bot protections, or access controls.

## Remaining hardening work

- Durable database-backed storage instead of in-memory ledgers.
- Encrypted secrets management.
- Authentication and authorization for the dashboard.
- Per-source rate limits and circuit breakers.
- OpenTelemetry or equivalent production tracing.
- Human approval UI for outbound actions.
- Deployment and backup procedures.

