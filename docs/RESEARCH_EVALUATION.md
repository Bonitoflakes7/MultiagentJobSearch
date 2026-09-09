# Phase 11: Research-grade evaluation

## Benchmark design

Each benchmark case stores:

- job ID
- policy ID
- predicted score
- rank
- recommendation
- known usefulness outcome, if available
- explicit user approval, if available
- unsupported-claim flag
- duplicate flag

The dataset is versioned and validated before evaluation. Unknown outcomes are excluded from supervised metrics rather than treated as failures.

## Metrics

- Top-k precision: useful recommendations among the top k labeled jobs.
- Top-k recall: useful labeled jobs found in the top k.
- Mean reciprocal rank: how early the first useful job appears.
- Brier score: calibration error for score-as-probability behavior; lower is better.
- User approval rate: explicit user approval, not inferred satisfaction.
- Unsupported-claim rate: safety quality indicator.
- Duplicate rate: ingestion quality indicator.

## Comparing policies

`compare_reports` produces metric deltas. The Phase 7 champion/challenger governance rules remain responsible for promotion. A higher ranking score alone is not sufficient if safety or unsupported-claim metrics worsen.

## Research limitations

- Rejection does not identify its cause unless the user supplies one.
- Interview probability requires more real labeled outcomes.
- Small samples can make metrics unstable.
- User approval is not the same as an interview or offer.
- Benchmark cases must be frozen before comparing policies to avoid evaluation drift.

