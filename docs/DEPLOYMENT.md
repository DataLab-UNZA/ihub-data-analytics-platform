# Deployment

The web app runs on **Google Cloud Run** in the project `ihub-data-analytics-platform` (region `africa-south1`, Johannesburg), owned by `lighton.phiri@unza.ac.zm`. Deployment is automatic: **merge to `main`, a member of `ihub-deployers` approves, and the app is live a few minutes later.** Merges that change only documentation, tests or the context pack (see the `paths-ignore` list in `deploy.yml`) do not start a deploy. Nobody needs Google Cloud access. The reasons for this design are in [ADR-002](decisions/ADR-002-hosting.md).

- **Public URL:** https://ihub-app-197899767407.africa-south1.run.app

## How it works

```
merge to main ──► Deploy workflow ──► waits for approval (production) ──► build 2 images ──► Cloud Run
Monday 02:00 UTC ──► Pipeline workflow ──► connectors + dbt ──► release data-YYYY-MM-DD
                                     └──► redeploy the commit already live, with the new data
```

| Workflow | When it runs | What it does |
|---|---|---|
| `CI` (`ci.yml`) | every PR and push to `main` | ruff and pytest, plus `npm run lint` and `npm run build` for `web/`; must pass before a PR can merge |
| `Deploy` (`deploy.yml`) | every push to `main` that changes the app; by hand; called by Pipeline | downloads the newest `data-*` release, builds the `api` image (`Dockerfile.api`, data built in) and the `web` image (`web/Dockerfile`), pushes both to Artifact Registry, applies `deploy/service.yaml` to `ihub-app`, checks `/healthz` and `/overview`, and writes the URL to the run summary |
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
| `IHUB_AUTH_SECRET`, `IHUB_GOOGLE_CLIENT_SECRET`, `IHUB_SMTP_PASSWORD` | **secrets of both the `production` and `pipeline` environments** | Deploy (passed to the `api` container) |
| `IHUB_GOOGLE_CLIENT_ID`, `IHUB_SMTP_HOST`, `IHUB_SMTP_PORT`, `IHUB_SMTP_USERNAME`, `IHUB_SMTP_FROM`, `IHUB_SMTP_SSL`, `IHUB_ALLOWED_EMAIL_DOMAIN`, `IHUB_BOOTSTRAP_ADMINS`, `IHUB_PUBLIC_URL` (optional) | repository **variables** | Deploy (passed to the `api` container) |

Set them in GitHub → **Settings → Environments → pipeline** (or **production**) **→ Environment secrets** (secrets) or **Settings → Secrets and variables → Actions → Variables** (variables). Secrets live in environments rather than the repository because those environments only run on `main`: a workflow on a branch cannot read them. Every name is also in `.env.example` for local use.

The sign-in secrets go in **both** environments because the Deploy job runs in `production` for a merge or a manual deploy, and in `pipeline` for the weekly redeploy; a secret missing from one would be dropped from the live app on that kind of deploy. Deploy writes each sign-in value that is set into the `api` container of `deploy/service.yaml` (unset values are left out) and never prints them. `IHUB_PUBLIC_URL` defaults to the service's own address. Note that values passed this way are visible to anyone who can view the Cloud Run service in Google Cloud; Secret Manager (ADR-008) is the stronger option for later.

### Google OAuth callback

For Google sign-in, the OAuth client must contain the exact HTTPS callback that the API sends to Google. In Google Cloud Console → **APIs & Services** → **Credentials** → the iHub web client, add:

- **Authorized JavaScript origin:** `https://ihub-app-zvmmzc2oja-bq.a.run.app`
- **Authorized redirect URI:** `https://ihub-app-zvmmzc2oja-bq.a.run.app/auth/google/callback`

Set the same base address as the GitHub repository variable `IHUB_PUBLIC_URL`. `localhost` is only for local development and cannot receive the production OAuth callback. If Cloud Run reports a different generated service URL after a future recreation, update both places together.

The Google Cloud resources were created once with [`scripts/gcp_setup.sh`](../scripts/gcp_setup.sh), run in Cloud Shell. It is safe to re-run and prints the values of the variables above.

## Sign-in (ADR-010)

Production requires sign-in. The current deployment uses an **instance-local SQLite account store** in `/tmp/ihub-auth.sqlite`, so it needs no cloud database. This is suitable for demonstrations only: every account, profile photo, email code and session disappears whenever Cloud Run stops, restarts, scales to zero or deploys a new revision. The app is limited to one instance, so users do not receive different account stores simultaneously.

Accounts are kept inside the app on purpose, with no cloud database (ADR-018). To set up sign-in:

1. Add the sign-in secrets and variables in GitHub (table above). The next deploy passes them to the `api`
   container.
2. In the Google Cloud console, list `<service URL>/auth/google/callback` as an authorised redirect URI of the OAuth client.
3. Leave `IHUB_PUBLIC_URL` empty (the deploy uses the `<service>-<project number>` address) or set it to the address people open.

Never put the secret values in GitHub variables, the repository or workflow logs: only in environment secrets.

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
- **What keeps it free:** at most one instance, and the instance stops about 15 minutes after the last request. Next.js keeps no connection open between requests, so open browser tabs do not keep the instance running. The instance has two containers of 1 vCPU each (2 vCPU in total), so the free tier covers about 25 instance-hours a month of active use.
- **Stop all spending at once:** `gcloud run services delete ihub-app --region africa-south1` in Cloud Shell. The next Deploy run recreates it.

### Trial end: action needed before February 8, 2027

The billing account began as a Google Cloud Free Trial ($300 credit, no automatic charges). On **February 8, 2027** the trial ends and the billing account closes unless it is **upgraded to a paid account** (Google Cloud console → **Billing** → **Upgrade**). Upgrade before that date, or the app stops. After the upgrade the free tier still applies, and the budget alert keeps reporting any charge.

## Running locally

```bash
uv run python -m ihub.ingest                          # creates data/ihub.duckdb
uv run uvicorn ihub.api.app:app --port 8000           # research API
cd web && npm install && npm run dev                  # http://localhost:3000
# With sign-in: fill the IHUB_* sign-in values in .env first; see web/README.md
```

To test the two containers together, as Cloud Run runs them:

```bash
docker build --file Dockerfile.api -t ihub-api .
docker build -t ihub-web web
docker run -d --rm --name ihub-api --network host ihub-api
docker run -d --rm --name ihub-web --network host ihub-web   # http://localhost:8080
curl localhost:8080/healthz
docker stop ihub-web ihub-api
```

## The service (`deploy/service.yaml`)

One Cloud Run service, `ihub-app`, with two containers in each instance ([ADR-007](decisions/ADR-007-nextjs-only-front-end.md)):

| Container | Image | Port | Role |
|---|---|---|---|
| `web` | `ihub/web` (`web/Dockerfile`) | 8080, receives all traffic | Next.js front end; calls the API at `http://127.0.0.1:8000` from the server only |
| `api` | `ihub/api` (`Dockerfile.api`) | 8000, localhost only | FastAPI research API over the DuckDB file built into the image |

The service explicitly uses Cloud Run ingress `all` and unauthenticated invocation, so its generated `run.app` URL is reachable by users and by the deployment health check.

`web` starts once `api` passes its startup probe (`/api/health`). The API is never reachable from the internet. The design-only screen index redirects to `/overview` in production; `IHUB_SHOW_PREVIEWS=true` shows it locally.
