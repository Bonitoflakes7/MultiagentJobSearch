# Phase 10: Integrations and production hardening

## Implemented boundaries

- `JobSourceAdapter`: typed contract for permitted job sources.
- `SavedInputAdapter`: offline adapter for pasted descriptions and saved URLs.
- `CompanyCareerPageAdapter`: bounded reader for explicitly allowlisted company career pages.
- `RssFeedAdapter`: bounded RSS/Atom reader for explicitly allowlisted feeds.
- `SourcePolicy` and `LiveHttpClient`: host allowlisting, terms-review requirement, timeout, response-size, item-count, user-agent, and retry limits.
- Retry policy: retries only configured transient exceptions with bounded attempts.
- Idempotency ledger: prevents duplicate operations.
- Approval gate: consequential actions require explicit approval before execution.
- Trace recorder: captures workflow events while redacting secret-like metadata.
- Runtime configuration: reads non-secret operational settings from environment variables.

## Action safety

The action gate supports prepared, approved, and executed states. It refuses unapproved execution and rejects duplicate execution keys. Email sending and application submission are not connected yet.

## Source safety

External source adapters must be explicitly permitted, respect source terms and rate limits, and return structured source items. They must not bypass authentication, bot protections, or access controls.

The live adapters are intentionally source-specific and conservative. They return untrusted `SourceItem` values; the Flow normalizes them and sends them through verification before matching or ranking. Failed fetches are retained on the adapter as bounded error messages and do not stop unrelated sources.

## Remaining hardening work

- Durable database-backed storage instead of in-memory ledgers.
- Encrypted secrets management.
- Authentication and authorization for the dashboard.
- Per-source rate limits and circuit breakers.
- Terms-of-service review records and production source configuration.
- OpenTelemetry or equivalent production tracing.
- Human approval UI for outbound actions.
- Deployment and backup procedures.
