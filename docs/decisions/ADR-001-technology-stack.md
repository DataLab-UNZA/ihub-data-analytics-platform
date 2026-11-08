# ADR-001: Technology stack

- **Status:** Accepted
- **Date:** November 8, 2026
- **Decided by:** Lighton Phiri

## Context

We need a prototype research analytics platform for UNZA. It must be built by four students whose strongest language is Python. It must be hosted at no cost, with no paid database, and keep all secrets out of the repository. Later it must take in other university systems (SIS, LMS, HR/payroll) without rework.

## Decision

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.12 | The team's strongest language, and well supported by every library below. |
| Environment and packaging | uv + `pyproject.toml` + `uv.lock` | One fast tool for reproducible installs. |
| Connectors | Plain Python classes behind a shared `Connector` interface (`httpx`, `tenacity`) | Readable and extensible: a new source is a new subclass. |
| OAI-PMH | Sickle | Mature client that handles resumption tokens (DSpace, OJS). |
| Raw layer | JSON Lines files loaded into a DuckDB `raw` schema | Data is kept exactly as fetched, so transforms can be re-run without fetching again. |
| Transforms | dbt-core + dbt-duckdb | Its staging/intermediate/marts conventions match our design, and it adds data tests, lineage docs and seeds. |
| Storage | DuckDB, as a single file | Free, fast for analytics, no server. |
| Web interface | Streamlit (multipage) + Plotly | Pure Python, so the students can contribute quickly. Its URL query parameters allow linkable pages for each record type. |
| Data access | `ihub.mart` query layer | Keeps SQL out of the UI, so the UI can be replaced later. |
| Pipeline | Scheduled GitHub Action | Free for public repositories. |
| Data publication | DuckDB file as a GitHub Release asset | Free and versioned. |
| Hosting | Google Cloud Run (min instances 0), with the DuckDB file built into the image | Within the free tier, and each deployment is immutable. |
| Deployment auth | Workload Identity Federation | No long-lived service-account key exists anywhere. |
| Quality | ruff, pytest, pre-commit, GitHub Actions CI | Fast, and simple enough for the students to learn. |

## Consequences

- The students write transforms in SQL (dbt) and connectors and app code in Python.
- Streamlit limits fine-grained layout control. If that becomes a problem, only `src/ihub/app/` needs replacing (e.g. with FastAPI + HTMX).
- Cloud Run requires a billing account linked to the GCP project, even when usage stays within the free tier.
- Research metadata is public, so publishing the DuckDB file publicly is acceptable. **Sensitive future sources (student, HR, payroll data) must not use this route.** They will need private storage (e.g. a private GCS bucket) and access control, decided in a separate ADR before that work starts.

## Alternatives considered

- **FastAPI + HTMX/Jinja UI:** more control, but the students would have to learn HTML templates. Deferred.
- **dlt for ingestion:** capable, but plain connector classes are easier for the students to follow.
- **pandas-only transforms:** familiar, but no built-in data tests or lineage. dbt was preferred.
- **Postgres/managed databases:** ruled out by the no-cost constraint.
