# Demonstration prompts: stage 1 walking skeleton

These prompts show the team how prompting Claude and deploying work, by building a first version of the dashboard that follows the whole pipeline (pull → pre-process → de-duplicate → data marts → render). Each prompt is one small step that can be reviewed before the next one. Run them in order in a Claude session on the repository (Lighton's Max account), with each Navigator logging their prompt in the Prompt Log first.

Stage 1 uses OpenAlex only, so the de-duplication step works within one source; it is built so that the other sources (ORCID, IRIM, OJS) plug into the same steps in stage 2.

---

## Prompt 0: context (once, at the start of the session)

```
Read README.md, CLAUDE.md, docs/ROADMAP.md, docs/DEPLOYMENT.md and docs/decisions/ before doing anything. We are building stage 1 of docs/ROADMAP.md, the walking skeleton: OpenAlex only, end to end, as small reviewable steps. Follow the "Guided answers and commit credit" rules in CLAUDE.md: whenever we need to decide something, give us 2 to 4 numbered options with the trade-off and your recommendation, and wait for our number. Do not write code yet. Reply with a five-line summary of the pipeline and the files each step will touch.
```

## Prompt 1: plan

```
Propose a plan for stage 1 as five steps that match our pipeline: (1) pull UNZA works from OpenAlex into their own staging database, (2) pre-process them with dbt staging models, (3) de-duplicate, (4) build a first mart, (5) render an Overview page. For each step list the files, the test, and how we will know it worked. First look up UNZA's OpenAlex institution ID and ROR ID from the OpenAlex API and show us the evidence; do not guess. Give us numbered options where there is a real choice (for example how many years of works to pull for the first version). Wait for our approval.
```

## Prompt 2: pull (connector → staging database)

```
Implement step 1 only. Add an OpenAlex connector in src/ihub/connectors/openalex.py that subclasses Connector, pulls works with an authorship affiliated to UNZA (use the institution ID we confirmed, OPENALEX_MAILTO for the polite pool and OPENALEX_API_KEY if set), and writes them unchanged into their own staging database: the raw_openalex schema in data/ihub.duckdb, with source name and fetch time. Register it in python -m ihub.ingest. Add a pytest test that uses a small recorded sample response; tests must not call the live API. Run ruff and pytest, then show us the row count from one live run and stop.
```

## Prompt 3: pre-process

```
Implement step 2 only. Add dbt staging models in transform/models/staging/openalex/ (stg_openalex__works and stg_openalex__authorships) that rename columns, set types, normalise DOIs (lower case, no https://doi.org/ prefix), and keep the OpenAlex ID as the source key. Add dbt tests for not-null and unique keys. Run dbt build and show us 5 sample rows and the test results.
```

## Prompt 4: de-duplicate

```
Implement step 3 only. Add transform/models/intermediate/int_publications__deduplicated.sql. Match publications on normalised DOI first, then on normalised title + year + first-author surname, as CLAUDE.md describes. Give every publication one publication_key and keep a row per source record in a bridge (bridge_publication_source) so we can later see which sources each publication came from. With only OpenAlex loaded this mainly removes duplicates within OpenAlex, but write it so ORCID, IRIM and OJS staging models can be added with one union each. Show us how many duplicates were found and two examples.
```

## Prompt 5: data mart

```
Implement step 4 only. Build a first version of the research mart in transform/models/marts/research/: fact_publication (one row per de-duplicated publication, with year, type, is_oa, oa_status, cited_by_count, n_authors, in_openalex), dim_year and dim_publication_type. Add read-only query functions in src/ihub/mart/research.py (publications_per_year, oa_share_per_year, top_venues, headline_counts) with type hints and tests on a tiny DuckDB fixture. Pages will only call these functions.
```

## Prompt 6: render

```
Implement step 5 only. Before writing code, describe how SciVal, Dimensions and the OpenAlex web interface lay out an institution overview, and give us 2 or 3 numbered layout options for our Overview page. After we choose, build src/ihub/app/pages/1_Overview.py with headline counts (publications, open-access share, citations), a publications-per-year chart, an open-access share trend and a top-venues table, using Plotly and one global year-range filter in the sidebar. The page must call ihub.mart functions only, with no SQL, and must call pause_when_idle(). Run it locally and show us a screenshot.
```

## Prompt 7: commit, pull request and deploy

```
We are ready to commit. Ask us whose change this is and who reviewed it, with numbered options from the Team tab, and read the matching Prompt Log rows for the trailers, as CLAUDE.md describes. Then commit on a feature branch, push, and open a pull request into main with a short description of what the team built. When CI passes, merge it, then show us the Deploy run waiting for approval so that a member of ihub-deployers can approve it, and give us the live URL once it is deployed.
```

After the merge, run the **Pipeline** workflow by hand (Actions → Pipeline → Run workflow) so that the live app is rebuilt with real OpenAlex data.

---

## Single prompt (when time is short)

```
Read README.md, CLAUDE.md, docs/ROADMAP.md and docs/DEPLOYMENT.md. Build stage 1 of the roadmap, the walking skeleton, following our pipeline: an OpenAlex connector that pulls UNZA works into their own staging database (raw_openalex schema), dbt staging models that clean them, an intermediate model that de-duplicates publications (DOI first, then title + year + first-author surname) with a source bridge, a first research mart (fact_publication, dim_year, dim_publication_type) with read-only query functions in ihub.mart, and a Streamlit Overview page with headline counts, publications per year, open-access share and top venues, plus a global year filter. Look up UNZA's OpenAlex institution ID first and show us the evidence. Work in small steps: after each step, stop, show us what changed and how it was checked, and give us numbered options for the next decision. Before committing, ask us whose change it is and who reviewed it, with numbered options from the Team tab, then open a pull request so the merge deploys through the production approval.
```
