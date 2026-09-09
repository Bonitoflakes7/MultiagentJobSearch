# Phase 18: Matching and Recommendation Response

Recommendations are generated from structured records, not from a free-form LLM paragraph.

For each ranked job, `JobRecommendation` combines:

- normalized title, company, location, and posting age;
- verification status;
- deterministic fit score and confidence;
- ranking tier and action;
- match-dimension evidence and gaps;
- resume proposals supported by candidate evidence;
- blocked unsupported resume claims;
- the ranking score breakdown explaining priority.

The Markdown renderer is `render_recommendation_markdown` in `src/job_search_ai/presentation/dashboard.py`. The dashboard snapshot exposes these records under `recommendations`, and the digest includes them under `Structured recommendations`.

An agent may improve wording later, but it must format these facts without adding claims. Verification, scoring, ranking, and resume safety remain authoritative.
