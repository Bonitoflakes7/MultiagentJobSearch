# Phase 13: Database and durable state

## Storage

The application uses SQLite for the first durable implementation. The repository is implemented in `app/storage.py` and creates the schema automatically.

## Stored records

- Workflow runs
- Candidate profile versions
- Canonical jobs
- Verification result versions
- Match analysis versions
- Resume analysis versions
- Ranking decisions per workflow run
- Agent evaluations by output, agent, and evaluator version
- Memory events
- Approval requests
- Application outcomes

## Immutability and retries

Versioned result tables use composite primary keys and `INSERT OR IGNORE`. Retrying a workflow does not duplicate the same snapshot or overwrite historical results. New agent or policy versions create new records.

## Run with persistence

```text
python -m app.main --smoke --database data/job_search.sqlite3
```

The database path should be kept outside source control. For production, it should eventually be replaced or backed by a managed database with backups, migrations, access control, and encryption at rest.

## Phase 13 test

The test suite creates a temporary SQLite database, saves a complete pipeline result, closes the connection, reopens it, and verifies that jobs, verification results, matches, rankings, and both agent evaluations remain available.

