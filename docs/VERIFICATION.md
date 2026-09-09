# Phase 3: Job verification and safety gates

## What this phase does

The verifier checks normalized records before matching or ranking. Each check returns a status, reason, and evidence. The aggregate status is one of:

- `verified`: all offline checks pass.
- `uncertain`: no hard failure, but missing or ambiguous information requires review.
- `rejected`: a hard rule fails, such as a stale listing or a clear seniority mismatch.
- `needs_review`: safety-sensitive content, such as agent-directed instructions, is present.

## Current checks

- URL shape: HTTP(S) URL validation; no network request yet.
- Completeness: title, company, location, and description.
- Freshness: posting date against a configurable age window, defaulting to 7 days for this job search.
- Location: Bangalore, Kerala, and Pune by default.
- Experience: fresher/0-1 year compatibility and seniority signals.
- Role relevance: target-role term detection.
- Content safety: prompt-injection-like instructions are flagged and never followed.
- Duplicate groups: shared normalized fingerprints are returned explicitly.

## Deliberate limitations

This phase does not claim that a company is legitimate, that a URL is reachable, or that a posting is still accepting applications. Those require permitted source access and evidence. Until then, such facts remain uncertain rather than being invented.

The default freshness policy rejects postings older than 7 days. Missing, future, or unparseable dates remain uncertain and require review. Relative labels such as `2 days ago`, `yesterday`, and `today` are supported when the verification reference date is known.

## Phase 3 test result

The automated test suite covers verified, stale, senior, incomplete, injection-containing, and duplicate listings. Run:

```text
python -m unittest discover -s tests -v
```
