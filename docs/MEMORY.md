# Phase 8: Memory and learning from feedback

## Memory types

The first memory layer uses an append-only event ledger with three event families:

- Preference feedback: explicit likes and dislikes from the user.
- Application outcomes: applied, rejected, interview, offer, withdrawn, or unknown.
- Agent feedback: evaluator observations about a particular agent output.

## Learning rules

- Explicit user feedback can update preference signals.
- Application outcomes update prediction metrics, not personal preferences.
- Rejections without a known reason are counted as unexplained outcomes.
- Every event has an ID and duplicate IDs are ignored for retry safety.
- Learning snapshots are derived from history and can be regenerated.
- Historical events are never edited in place.

## Current storage

`MemoryLedger` supports JSONL persistence and replay. Database-backed storage, encryption, retention controls, and user-facing memory management belong to later hardening work.

## What this prevents

The system will not learn “avoid backend jobs” merely because one backend application was rejected. It needs explicit preference feedback for that conclusion. This keeps prediction errors separate from personal taste.

