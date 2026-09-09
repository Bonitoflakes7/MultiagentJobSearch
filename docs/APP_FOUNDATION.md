# Phase 12: Application foundation

## Current status

The real application shell now has an application service at `app/pipeline.py`, a CLI entry point at `app/main.py`, and an optional CrewAI boundary at `app/crew/flow.py`. The service composes the validated domain pipeline without network calls or outbound side effects.

Run it with:

```text
python -m app.main --smoke
```

To exercise the actual CrewAI Flow boundary:

```text
python -m unittest tests.test_crew_flow -v
```

CrewAI's local storage is redirected to ignored project paths under `data/crewai/` and `data/crewai-localappdata/` so the application does not depend on unavailable platform user-data directories.

## CrewAI boundary

CrewAI is declared in `requirements.txt`. The Flow adapter is import-safe when CrewAI is unavailable and uses an offline fallback with the same public behavior. This preserves deterministic validation and makes CrewAI responsible for orchestration rather than truth or permissions.

## Phase 12 acceptance criteria

- Application service composes all validated stages.
- CLI smoke command returns a machine-readable status.
- Governance results are included in the application result.
- No network or outbound side effects occur in smoke mode.
- CrewAI dependency is installed and the first Flow boundary executes successfully without an LLM API key.
