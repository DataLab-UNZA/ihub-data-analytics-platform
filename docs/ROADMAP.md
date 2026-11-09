# Roadmap

**Goal:** a data analytics dashboard for the research output of the University of Zambia (UNZA). Lighton Phiri will add further requirements as the project goes on; they are added here as new stages or items.

**Ownership:** until we have a minimal product (the mid-point review target below), nobody owns a part of the system. The team works as a mob and picks the next task together. Ownership is agreed after the minimal product is in place.

## The pipeline every stage follows

```
OpenAlex ─┐
ORCID ────┤  1. pull each source      2. pre-process      3. de-duplicate       4. data marts       5. render
IRIM ─────┤  into its own staging  ─► each source      ─► across sources    ─► (star schema)   ─► Streamlit
OJS (15) ─┘  database (raw schema)    (dbt staging)       (dbt intermediate)    (dbt marts)          dashboard
```

1. **Pull:** one connector per source (`src/ihub/connectors/`) writes records exactly as fetched into that source's own staging database (a `raw_<source>` schema in `data/ihub.duckdb`).
2. **Pre-process:** dbt staging models, one folder per source (`transform/models/staging/<source>/`), rename, type and standardise (DOIs, names, dates, departments). No joins across sources.
3. **De-duplicate:** dbt intermediate models match records found in more than one source. Publications match on DOI first, then normalised title + year + first-author surname; authors match on ORCID first, then OpenAlex ID. Every record keeps a link to each source it came from.
4. **Data marts:** the research star schema in `CLAUDE.md`.
5. **Render:** Streamlit pages that call `src/ihub/mart/` (never SQL in pages), deployed to Google Cloud Run.

## Stages

| Stage | What is delivered | Status |
|---|---|---|
| 0. Foundations | Repository, CI, automatic deployment to Cloud Run, weekly data pipeline, live app | Done, November 9, 2026 |
| 1. Walking skeleton | OpenAlex only, end to end: UNZA works pulled into staging, cleaned, a first mart, a first Overview page live | Next |
| 2. All sources in staging | Connectors for ORCID, the UNZA institutional repository (IRIM) and the 15 OJS journals, each with tests on recorded sample responses and its own staging tables | |
| 3. Pre-processing | Staging models for every source | |
| 4. De-duplication | Cross-source matching of publications and authors, with source links kept | |
| 5. Data marts | The full research star schema | |
| 6. Dashboard | Overview, Publications explorer (filters, CSV export, links to DOI, repository or OJS record), Departments, Authors, Journals and Source coverage pages, with one global year filter | |

**Mid-point review target (the minimal product):** stages 1 to 4 working for all four sources, with the Overview and Publications explorer pages live on real data. After the review, each student takes ownership of an area, and stages 5 and 6 are completed together with any new requirements.

**Out of scope for iteration 1** (see `CLAUDE.md`): Google Scholar, field-weighted citation metrics, benchmarking against other universities, grants and patents, staff league tables, user accounts, editable profiles and network graphs. Later iterations add other UNZA systems (student information, LMS, HR/payroll, staff performance, promotions).

## Before the connector work starts

These values are still to be verified (see `config/sources.yml`): UNZA's ROR ID and OpenAlex institution ID, the IRIM OAI-PMH endpoint and metadata formats, the OJS base URL and journal paths, ORCID client credentials, the OpenAlex contact email and API key, and the source for the schools-to-departments seed.

Tasks for each stage are [GitHub issues](https://github.com/DataLab-UNZA/ihub-data-analytics-platform/issues), labelled by layer. Demonstration prompts for stage 1 are in [`DEMO_PROMPTS.md`](DEMO_PROMPTS.md).
