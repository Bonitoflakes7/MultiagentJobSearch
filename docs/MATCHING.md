# Phase 4: Matching and explainable scoring

## Baseline scoring model

The deterministic baseline uses five dimensions:

| Dimension | Weight |
| --- | ---: |
| Role relevance | 25% |
| Skill match | 30% |
| Experience compatibility | 20% |
| Location compatibility | 15% |
| Domain and project evidence | 10% |

The result is a weighted score from 0 to 100. This is a starting policy, not an unquestionable truth. Later evaluation phases will measure whether these weights predict useful opportunities for the candidate.

## Recommendation bands

- `apply_priority`: 80-100
- `apply_review`: 65-79.99
- `stretch_review`: 50-64.99
- `do_not_prioritize`: below 50
- `blocked`: verification rejected the job or the content requires safety review

## Explainability requirements

Every result stores:

- dimension score and weight
- matched evidence
- skill gaps
- confidence
- verification warnings
- hard constraints
- matching-policy version
- input record ID

The score does not mean probability of an interview. It is a transparent compatibility score until real application outcomes provide calibration data.

## Safety and honesty rules

- A missing skill is a gap, not proof that the candidate cannot perform the job.
- A keyword match is not automatically proof of experience.
- An uncertain verification result produces a warning.
- A rejected or safety-sensitive job cannot receive a normal apply recommendation.
- Matching reads a profile snapshot and cannot mutate candidate evidence.

