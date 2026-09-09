# Phase 1 test report

## Completed checks

- Resume text extracted from the supplied one-page PDF.
- Resume page visually inspected for section structure and content alignment.
- Candidate preferences incorporated from the user's request.
- Current internship preserved as experience rather than discarded under the fresher label.
- Additional HealthRecord AI project recorded separately as user-supplied evidence.
- Python/backend/AI skills separated from secondary JavaScript-framework evidence.
- Missing preferences marked as unknown rather than guessed.
- Contact details excluded from the matching profile used by agents.

## Phase 1 decisions

- Search band: fresher / 0-1 years.
- Current internship: relevant experience, but not disqualifying for fresher roles.
- Location matching: Bangalore, Kerala, and Pune.
- Salary: no filtering constraint.
- Company type: startup and MNC equally acceptable.
- React/Redux: allowed as supporting evidence, but JavaScript-framework-heavy roles should be down-ranked.
- HealthRecord AI: usable for matching, but should be added to the resume evidence source before resume tailoring treats it as resume-present evidence.

## Manual review requested before Phase 2

These are not blockers for continuing, but confirming them later will improve ranking:

1. Is any work arrangement acceptable, or should onsite/hybrid/remote be prioritized?
2. Should all Kerala locations be included, or only specific cities?
3. Should Go-only backend roles be included as secondary opportunities?
4. Should data/ML engineer roles be included as secondary opportunities?

## Result

Phase 1 passes its current acceptance criteria. The next phase can ingest and normalize job records against this profile.

