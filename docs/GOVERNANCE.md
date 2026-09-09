# Phase 7: Evaluator and governance layer

## Evaluation rubric

Agent outputs are evaluated on:

- schema completeness
- evidence grounding
- safety and constraint compliance
- usefulness of explanations
- calibration, where enough outcome data exists

The evaluator stores the agent version, evaluator version, input snapshot ID, rubric scores, findings, feedback, and timestamp.

## Severity

- `info`: observation only
- `warning`: quality concern, but not necessarily unsafe
- `error`: output should not be promoted without correction
- `critical`: output must fail and be blocked from normal use

## Champion/challenger governance

The active policy is the champion. A proposed policy is a challenger. The comparison process:

1. Runs both versions against the same benchmark or historical sample.
2. Calculates quality, safety, unsupported-claim, and top-five usefulness deltas.
3. Requires minimum sample size and quality improvement.
4. Rejects any challenger with safety or evidence regression beyond configured thresholds.
5. Returns `promote_challenger` or `retain_champion`.
6. Preserves both versions and the comparison record; it never rewrites historical results.

This implements the “last best versus new best” behavior required for safe self-improvement.

## Current limitation

Calibration is provisional until real application outcomes exist. The evaluator must not pretend that its own score proves interview probability.

