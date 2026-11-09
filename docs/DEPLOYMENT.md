# Deployment

The web app runs on **Google Cloud Run** in the project `ihub-data-analytics-platform` (region `africa-south1`, Johannesburg), owned by `lighton.phiri@unza.ac.zm`. Deployment is automatic: **merge to `main`, a member of `ihub-deployers` approves, and the app is live a few minutes later.** Merges that change only documentation, tests or the context pack (see the `paths-ignore` list in `deploy.yml`) do not start a deploy. Nobody needs Google Cloud access. The reasons for this design are in [ADR-002](decisions/ADR-002-hosting.md).

- **Public URL:** https://ihub-app-197899767407.africa-south1.run.app

## How it works

```
merge to main ──► Deploy workflow ──► waits for approval (production) ──► build image ──► Cloud Run
Monday 02:00 UTC ──► Pipeline workflow ──► connectors + dbt ──► release data-YYYY-MM-DD
                                     └──► redeploy the commit already live, with the new data
```

| Workflow | When it runs | What it does |
|---|---|---|
| `CI` (`ci.yml`) | every PR and push to `main` | ruff and pytest; must pass before a PR can merge |
| `Deploy` (`deploy.yml`) | every push to `main` that changes the app; by hand; called by Pipeline | downloads the newest `data-*` release, builds the image, pushes it to Artifact Registry, deploys `ihub-app`, checks `/_stcore/health` and writes the URL to the run summary |
| `Context pack` (`context-pack.yml`) | every push to `main`, issue changes; by hand | rebuilds the context pack for Claude chats and publishes it on the `context-pack` release (no deploy) |
| `Pipeline` (`pipeline.yml`) | Mondays 02:00 UTC (04:00 in Lusaka); by hand | runs `python -m ihub.ingest` and `dbt build`, publishes `ihub.duckdb` as `data-YYYY-MM-DD` (keeps the 5 newest), then redeploys the live commit with that data |

GitHub Actions signs in to Google Cloud with **Workload Identity Federation**: GitHub issues a short-lived token for each run, and Google accepts it only from this repository's `main` branch. No key or password for Google Cloud is stored anywhere, so a workflow on a student's branch cannot deploy.

## Approving a deployment

After a merge, the Deploy run pauses with **"Waiting for review"**. Any member of the `ihub-deployers` team (Lighton and the four students) can approve it; `mubanga-chibesa` is also listed as an individual reviewer:

1. GitHub → **Actions** → the waiting **Deploy** run → **Review deployments**.
2. Tick **production** → **Approve and deploy**.

GitHub records who approved each deployment (repository → **Environments** → **production**). Weekly data refreshes use the `pipeline` environment and need no approval, because they redeploy code that is already live.

To change who can approve: DataLab-UNZA organisation → **Teams** → `ihub-deployers` → add or remove members.

## Where settings and secrets live

| Name | Kind | Used by |
|---|---|---|
| `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`, `GCP_RUNTIME_SA` | repository **variables** (not secret) | Deploy, Pipeline |
| `OPENALEX_MAILTO` | repository **variable** | Pipeline |
| `OPENALEX_API_KEY`, `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `OJS_API_TOKEN` | **secrets of the `pipeline` environment** | Pipeline only |

Set them in GitHub → **Settings → Environments → pipeline → Environment secrets** (secrets) or **Settings → Secrets and variables → Actions → Variables** (variables). The API secrets live in the environment rather than the repository because the `pipeline` environment only runs on `main`: a workflow on a branch cannot read them. The running app needs no secrets. Every name is also in `.env.example` for local use.

The Google Cloud resources were created once with [`scripts/gcp_setup.sh`](../scripts/gcp_setup.sh), run in Cloud Shell. It is safe to re-run and prints the values of the variables above.

## How to roll back

- **Code (fastest):** GitHub → **Actions** → **Deploy** → **Run workflow**, put the commit you want back in **ref** (for example the previous merge on `main`), run it and approve it. The image is rebuilt from that commit with the newest data.
- **Code (permanent):** revert the offending commit through a PR. When it merges and is approved, the previous behaviour is live again.
- **Instant, from Cloud Shell:** send all traffic to an earlier revision:
  ```bash
  gcloud run revisions list --service ihub-app --region africa-south1
  gcloud run services update-traffic ihub-app --region africa-south1 --to-revisions REVISION=100
  ```
  The next deploy sends traffic to the newest revision again.
- **Data:** delete the newest `data-*` release (GitHub → **Releases**), then run **Deploy** by hand to rebuild with the previous release.

## How to check costs

The expected cost is $0: the app scales to zero when nobody is using it, and its usage falls within Cloud Run's free tier (about 50 instance-hours a month at 1 vCPU).

- **Budget alert:** "iHub monthly budget", $5 a month on this project, emails the billing administrators at 10%, 50% and 100% of actual spend and at 100% of forecast spend. It counts costs before credits, so it reports real usage even while trial credit is paying.
- **Look at spend:** [Billing reports](https://console.cloud.google.com/billing/01AAD0-7EDB2F-48669E/reports?authuser=lighton.phiri@unza.ac.zm), filtered to project `ihub-data-analytics-platform`.
- **Look at usage:** Cloud Run → `ihub-app` → **Metrics** (instance count, billable instance time).
- **What keeps it free:** at most one instance; the instance stops about 15 minutes after the last request; browser tabs left open are paused after 20 minutes without activity (`src/ihub/app/idle.py`), which closes their connection.
- **Stop all spending at once:** `gcloud run services delete ihub-app --region africa-south1` in Cloud Shell. The next Deploy run recreates it.

### Trial end: action needed before February 8, 2027

The billing account began as a Google Cloud Free Trial ($300 credit, no automatic charges). On **February 8, 2027** the trial ends and the billing account closes unless it is **upgraded to a paid account** (Google Cloud console → **Billing** → **Upgrade**). Upgrade before that date, or the app stops. After the upgrade the free tier still applies, and the budget alert keeps reporting any charge.

## Running locally

```bash
uv run python -m ihub.ingest                  # creates data/ihub.duckdb
uv run streamlit run src/ihub/app/Home.py     # http://localhost:8501
```

To test the container locally:

```bash
docker build -t ihub-app .
docker run --rm -p 8080:8080 ihub-app        # http://localhost:8080
```
