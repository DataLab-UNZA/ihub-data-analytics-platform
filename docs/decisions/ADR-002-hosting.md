# ADR-002: Hosting and deployment on Google Cloud Run

- **Status:** Accepted
- **Date:** November 9, 2026
- **Decided by:** Lighton Phiri (session 02, Deployment)

## Context

The prototype must be publicly reachable at no cost, and deployment must be fully automated: merging to `main` deploys the app, and nobody opens a cloud console during a mob session. ADR-001 chose Google Cloud Run with the DuckDB file built into the image.

An earlier pull request (#1) moved hosting to Streamlit Community Cloud because no payment method was available. It was reverted in full (#2): Lighton created a Google Cloud billing account under `lighton.phiri@unza.ac.zm`, which removes that blocker and keeps the platform under the project's own account.

Facts checked on November 9, 2026 ([Cloud Run pricing](https://cloud.google.com/run/pricing)):

- Cloud Run's always-free tier (request-based billing) gives 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds per month, pooled per billing account and applied as a Tier 1 discount.
- `africa-south1` (Johannesburg) is a **Tier 1** region, so it gets the full free tier and is the closest region to Zambia.
- Cloud Run needs a billing account with a payment method, even within the free tier.
- A Streamlit page holds an open connection to the server, and Cloud Run bills the instance while any connection is open. At 1 vCPU the free tier covers about 50 instance-hours a month; several viewers on one instance count once.

## Decision

1. **Host on Cloud Run** in a dedicated project, `ihub-data-analytics-platform`, owned by `lighton.phiri@unza.ac.zm`, region `africa-south1`.
2. **Service `ihub-app`:** minimum 0 and maximum 1 instances, 1 vCPU, 512 MiB, CPU only while serving requests, concurrency 80, 60-minute request timeout, session affinity, public access without an `allUsers` IAM binding (`--no-invoker-iam-check`). It runs as `ihub-app-runtime`, a service account with no roles.
3. **Image:** `python:3.12-slim` with uv and the app's runtime dependencies only. The newest `data-*` release asset `ihub.duckdb` is copied in at build time. Images go to Artifact Registry repository `ihub`, which keeps the three newest.
4. **Keyless deployment:** GitHub Actions authenticates through Workload Identity Federation (pool `github`, provider `github-oidc`). The provider accepts only tokens from `DataLab-UNZA/ihub-data-analytics-platform` on `refs/heads/main`, and impersonates `github-deployer`, which holds only Cloud Run Admin, Artifact Registry Writer and permission to act as the runtime account. No service-account key exists.
5. **Workflows:** `deploy.yml` deploys every merge to `main` after approval in the `production` environment (any member of the `ihub-deployers` team may approve); it can also deploy an older commit by hand to roll back. `pipeline.yml` refreshes the data weekly and redeploys the commit that is already live with the new data, in the ungated `pipeline` environment, so a data refresh never ships unapproved code.
6. **Secrets:** API credentials (`OPENALEX_API_KEY`, `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `OJS_API_TOKEN`) are secrets of the `pipeline` environment, which only `main` can use; anyone with Write access could otherwise read repository-level secrets from a workflow on a branch. Non-secret values (`GCP_*`, `OPENALEX_MAILTO`) are repository variables. Google Secret Manager is not used, because the running app needs no secrets.
7. **Cost controls:** maximum one instance; idle browser tabs are paused after 20 minutes (`ihub.app.idle`) so the instance can scale to zero; a budget of $5 a month on the project emails the billing administrators at 10%, 50% and 100% of actual spend and at 100% of forecast spend, measured before credits.

## Consequences

- Expected cost is $0. The worst case, an instance kept busy all month, is roughly $60; the instance cap and idle pause make that unlikely, and the budget alert reports any spend within a day.
- The billing account started as a Free Trial ($300 credit) that ends on **February 8, 2027**. It must be upgraded to a paid account before then, or the billing account closes and the app stops. The free tier is unchanged after the upgrade.
- After about 15 minutes without visitors the instance scales to zero, so the first visit after that waits a few seconds for a cold start.
- Data is read-only inside the image; the weekly pipeline replaces it.
- Students deploy through GitHub only. None of them needs access to Google Cloud.

## Alternatives considered

- **Streamlit Community Cloud:** free and needs no card, but there is no approval step for deploys, resources are smaller and the app is hosted in the US. Used briefly in #1 and reverted.
- **Render free tier:** web services sleep after 15 minutes and take about a minute to wake, run on 0.1 CPU, and sources disagree on whether a card is needed. Rejected.
