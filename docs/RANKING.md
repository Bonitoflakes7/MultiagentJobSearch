# Phase 5: Ranking and daily action plan

## Ranking policy

The ranking score combines:

| Factor | Weight |
| --- | ---: |
| Match score | 65% |
| Match confidence | 15% |
| Freshness | 10% |
| Verification quality | 10% |

This prevents a high-fit but poorly verified job from automatically beating a slightly lower-fit job with stronger evidence.

## Tiers

- `S`: priority opportunity
- `A`: strong opportunity
- `B`: worthwhile opportunity
- `C`: stretch or lower-priority opportunity
- `D`: do not prioritize or blocked

## Daily plan

The daily plan is deliberately bounded. It selects at most a configured number of actions and converts each into one of:

- apply
- review verification
- tailor resume
- monitor
- skip

Applications are never submitted by this layer. It produces a queue for human review.

## Explainability

Each ranked result includes the score breakdown, reasons for priority, concerns, skill gaps, verification status, and rank. Ties are resolved deterministically using confidence and record ID so repeated runs do not randomly reorder jobs.

