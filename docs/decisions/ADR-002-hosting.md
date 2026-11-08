# ADR-002: Hosting and deployment

- **Status:** Accepted
- **Date:** November 9, 2026
- **Decided by:** Mubanga Chibesa (session 02, Deployment), following the brief from Lighton Phiri

## Context

The prototype must be publicly reachable **at no cost**, and deployment must be fully automated: merging to `main` deploys the app, and nobody opens a cloud console during a mob session. ADR-001 assumed Google Cloud Run with the DuckDB file built into the image.

During setup it became clear that **no payment method is available** to the team. This is decisive: Google Cloud Run — and essentially every container/VM platform with a free tier (Cloud Run, Fly.io, Railway, and now Render in most cases) — requires a billing account with a card to be linked before anything can be deployed, even when usage stays inside the free allowance. A card-free host is therefore a hard requirement, which rules Cloud Run out.

Facts checked on November 9, 2026:

- **Google Cloud Run** needs a billing account with a card linked to the project before a service can be created, even within the always-free tier. No card → no project → no deploy.
- **Streamlit Community Cloud** is free with **no card**: it deploys a Streamlit app straight from a public GitHub repo, redeploys automatically on every push to the tracked branch, serves a public `*.streamlit.app` URL, and puts the app to sleep after a period of inactivity (it wakes on the next visit, ~30 s). Dependencies come from `requirements.txt` or `uv.lock`; a `src/` layout needs the project installed editable (`-e .`) so the package imports.
- **Render's** free web service (the alternative in the brief) runs on 0.1 CPU with ~1-minute cold starts, the nearest region is Frankfurt, and 2026 sources disagree on whether it still allows a card-free account — too uncertain against a hard no-card, no-cost requirement.
- **Hugging Face Spaces** is also card-free and could reuse a Dockerfile, but needs a second git remote (the Space) mirrored from `main`, and is a worse fit for a plain Streamlit app than Streamlit's own host.

## Decision

1. **Host the app on Streamlit Community Cloud**, deploying from `main` with entry point `src/ihub/app/Home.py`. The app is connected to the repository once, by hand, at [share.streamlit.io](https://share.streamlit.io); after that every push to `main` redeploys automatically, so "merging to `main` deploys the app" holds with no deploy workflow and no console.
2. **Dependencies:** a root `requirements.txt` containing `-e .` installs the `ihub` package (and its `[project]` runtime dependencies from `pyproject.toml`) so the `src/` layout imports cleanly on Community Cloud. The dev and pipeline groups are not installed on the host; the running app needs neither.
3. **Data:** the pipeline keeps publishing `ihub.duckdb` as a `data-YYYY-MM-DD` GitHub Release asset (as in ADR-001). Instead of being baked into an image, **the app downloads the newest asset at runtime** (`ihub.mart.data_source`), cached for an hour, so the weekly data refresh appears without a redeploy. The repository is public, so no token is needed.
4. **Workflows:** `ci.yml` (ruff + pytest on every PR and push) and `pipeline.yml` (weekly, Mondays 02:00 UTC, or by hand; publishes the data release, keeps the last 5). No deploy, rollback or Docker workflow — Community Cloud handles deployment itself.
5. **Secrets:** the running app needs **none** (it reads only public data). The pipeline's API credentials (`OPENALEX_API_KEY`, `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `OJS_API_TOKEN`) are GitHub repository secrets; `OPENALEX_MAILTO` is a repository variable.

## Consequences

- **Truly $0 and no card.** There is no billing account, so nothing can be charged and no budget alert is needed.
- The app **sleeps after inactivity** and takes a few seconds to wake on the next visit. Acceptable for a prototype shown in sessions.
- Community Cloud has **modest resource limits** (about 1 GB RAM, shared CPU). Fine for the current prototype; if the app outgrows them, revisit hosting — the Cloud Run design in the git history can be restored once a billing account with a card exists.
- The one-time **connect at share.streamlit.io is manual** (Community Cloud has no API). It is done once, in this setup session, not during mob sessions.
- **Rollback** is by reverting the offending commit on `main` through a PR (Community Cloud redeploys the previous state); data is rolled back by deleting the newest `data-*` release so the app falls back to the previous one.
- This ADR **supersedes the Cloud Run hosting direction in ADR-001**. ADR-001's data design (DuckDB published as a public release asset) is kept; it is now consumed at runtime rather than built into an image.

## Alternatives considered

- **Google Cloud Run:** the original plan (1 vCPU, keyless Workload Identity Federation deploys, a region near Zambia). Blocked outright because it requires a billing account with a card, which the team does not have.
- **Render free tier:** 0.1 CPU and ~1-minute cold starts make Streamlit and DuckDB sluggish, and its card-free status in 2026 is uncertain. Rejected.
- **Hugging Face Spaces:** card-free and could reuse a Dockerfile, but needs a mirrored Space remote and is a worse fit for a plain Streamlit app. Kept as the fallback if Community Cloud's limits become a problem.
