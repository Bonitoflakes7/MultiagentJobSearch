# Evaluation and learning policy

## Evaluation layers

1. Schema validation: is the result complete and correctly typed?
2. Evidence validation: do claims point to candidate or job evidence?
3. Rule validation: did hard constraints and safety policies pass?
4. Quality rubric: is the reasoning accurate, useful, and well calibrated?
5. Outcome evaluation: did the recommendation perform well later?

## Versioning

Every agent, prompt, scoring policy, evaluator, and workflow definition receives a version. Results store the versions used to create them.

The current production policy is the champion. Proposed changes are challengers. A challenger must run against a fixed regression set and meet promotion thresholds before becoming champion.

## Important distinction

An application rejection is an outcome, not automatically a known cause. The system must record whether the reason is known, inferred, or unknown. Unknown outcomes must not create overly confident feedback.

## Initial metrics

- ingestion duplicate rate
- verification precision on manually reviewed samples
- missing-field rate
- evidence coverage
- ranking top-5 usefulness rate
- user approval rate
- resume suggestion acceptance rate
- unsupported-claim rate
- score calibration
- interview conversion by score band

