# Full project test runbook

## 1. Run the automated suite

From the project root:

```text
python -m unittest discover -s tests -v
```

This runs all unit, contract-style, workflow, infrastructure, dashboard, governance, memory, and research-evaluation tests.

## 2. Run the complete offline pipeline

```text
python scripts/run_end_to_end.py
```

Expected behavior:

- One strong Bangalore backend opportunity is verified and ranked highly.
- One Pune AI opportunity is available for review and exposes its Kubernetes gap.
- One senior role is rejected and blocked from normal action.
- Resume proposals do not fabricate missing skills.
- Governance evaluations pass.
- A dashboard and digest preview are generated in memory.
- Research metrics are printed.

The command exits with code `0` only if every governance evaluation passes.

## 3. Manual Phase 2-9 test with real listings

Prepare three or more job descriptions:

1. A strong Python/FastAPI/AI role in Bangalore, Kerala, or Pune.
2. A role with missing salary, date, or location information.
3. A role requiring more than one year of experience.
4. A role dominated by React/JavaScript requirements.
5. A suspicious description containing instructions addressed to the AI.

For each listing, inspect:

- normalized title, company, location, and skills
- verification status and reasons
- match score and confidence
- matched and missing skills
- ranking tier and action
- resume proposals and blocked claims
- evaluator findings

## 4. Human acceptance checklist

- Does the system rank the strongest relevant roles near the top?
- Does it distinguish unknown information from negative information?
- Does it reject senior roles for the fresher target band?
- Does it down-rank JavaScript-framework-heavy roles appropriately?
- Does it never claim unsupported experience?
- Does it expose why a role received its score?
- Does it keep uncertain jobs for review rather than silently discarding them?
- Does it separate personal preference feedback from application rejection?
- Does it require approval before an outbound action?

## 5. What is not yet a production test

The current suite does not yet test live websites, rate limits, email providers, authentication, browser automation, or actual job submissions. Those require explicit source selection, credentials, terms-of-service review, and a separate integration test environment.

