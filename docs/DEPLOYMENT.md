# Deployment

The web app is hosted on **Streamlit Community Cloud** (free, no card). It is connected to this repository once, by hand; after that **every push to `main` redeploys the app automatically** — nobody needs to open a console to deploy, and a weekly GitHub Action refreshes the data. The reasons for this design, and why it replaced the original Google Cloud Run plan, are in [ADR-002](decisions/ADR-002-hosting.md).

## How it works

```
merge to main ────────────► Streamlit Community Cloud redeploys automatically
Monday 02:00 UTC ─► Pipeline workflow ─► connectors + dbt ─► GitHub Release data-YYYY-MM-DD
                                                                      │
                     app downloads the newest data-* asset at runtime ◄┘ (hourly cache)
```

| Workflow | When it runs | What it does |
|---|---|---|
| `CI` (`ci.yml`) | every PR and push to `main` | ruff and pytest; must pass before a PR can merge |
| `Pipeline` (`pipeline.yml`) | Mondays 02:00 UTC (04:00 in Lusaka), or by hand | runs `python -m ihub.ingest` (connectors) and `dbt build`, publishes `ihub.duckdb` as release `data-YYYY-MM-DD` (keeps the 5 newest) |

There is no deploy or rollback workflow: Streamlit Community Cloud watches `main` and redeploys on every push itself. To run the pipeline by hand: GitHub → **Actions** → **Pipeline** → **Run workflow** (branch `main`).

The app does not bake the data into an image. On start-up it downloads the newest `data-*` release asset `ihub.duckdb` (`src/ihub/mart/data_source.py`) and re-checks hourly, so a new weekly data release appears without a redeploy. Until the pipeline has run once, the home page says no data is published yet.

## First-time setup (once, in the browser)

Connecting the app to Community Cloud is the only manual step, done once by someone signed in to the GitHub account that owns or can access the repository:

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub; authorise Streamlit for the `DataLab-UNZA` organisation.
2. **Create app** → **Deploy a public app from GitHub**.
3. Set:
   - **Repository:** `DataLab-UNZA/ihub-data-analytics-platform`
   - **Branch:** `main`
   - **Main file path:** `src/ihub/app/Home.py`
4. **Deploy.** The first build installs dependencies from `requirements.txt` (`-e .`) and starts the app. The public URL is `https://<chosen-subdomain>.streamlit.app`.

After this, no one touches Community Cloud again for normal work: pushes to `main` redeploy automatically.

### Where settings and secrets live

| Name | Kind | Used by |
|---|---|---|
| `OPENALEX_MAILTO` | GitHub repository **variable** | Pipeline |
| `OPENALEX_API_KEY`, `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `OJS_API_TOKEN` | GitHub repository **secret** | Pipeline only |

Set them in GitHub → **Settings → Secrets and variables → Actions**. Add the API secrets with `gh secret set <NAME> --repo DataLab-UNZA/ihub-data-analytics-platform` (gh prompts for the value) when they are available; none are needed for the first deployment. **The running app needs no secrets** — it reads only public data. Every name is also listed in `.env.example` for local use.

## How to roll back

- **Code:** revert the offending commit on `main` with a PR. When it merges, Community Cloud redeploys the previous state. (You can also use **Manage app → Reboot** on Community Cloud to restart the current version.)
- **Data:** delete the newest `data-*` release (GitHub → **Releases**). Within the hour the app's cache expires and it falls back to the newest remaining release; use **Reboot** on Community Cloud to pick it up immediately.

## How to check costs

There is nothing to check: Streamlit Community Cloud is free and has **no billing account**, so nothing can be charged. There is no budget alert because there is no spend to alert on. The only limits are technical, not financial:

- The app sleeps after inactivity and wakes (~30 s) on the next visit.
- Community Cloud allows about 1 GB of RAM and shared CPU per app. If the prototype outgrows this, see ADR-002 for the next step (Cloud Run, once a billing account with a card exists).

Check the app's health and logs from **Manage app** in the Community Cloud dashboard.

## Running locally

```bash
uv run python -m ihub.ingest          # creates data/ihub.duckdb
uv run streamlit run src/ihub/app/Home.py   # http://localhost:8501
```

With a local `data/ihub.duckdb` present, the app uses it directly and does not download a release asset.
