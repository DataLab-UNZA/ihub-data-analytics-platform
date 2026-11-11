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
| 1. Walking skeleton | OpenAlex only, end to end: UNZA works pulled into staging, cleaned, a first mart, a first Overview page live | Done (#9 to #11) |
| 2. All sources in staging | Connectors for ORCID, the UNZA institutional repository (IRIM) and the 15 OJS journals, each with tests on recorded sample responses and its own staging tables | Done (#12 to #16) |
| 3. Pre-processing | Staging models for every source, and the seeds for UNZA's schools, departments and their aliases ([ADR-003](decisions/ADR-003-staging-and-department-attribution.md)) | In review (#17, #18) |
| 4. De-duplication | Cross-source matching of publications and authors, with source links kept | |
| 5. Data marts | The full research star schema | |
| 6. Dashboard | Overview, Publications explorer (filters, CSV export, links to DOI, repository or OJS record), Departments, Authors, Journals and Source coverage pages, with one global year filter | |

**Mid-point review target (the minimal product):** stages 1 to 4 working for all four sources, with the Overview and Publications explorer pages live on real data. After the review, each student takes ownership of an area, and stages 5 and 6 are completed together with any new requirements.

**Out of scope for iteration 1** (see `CLAUDE.md`): Google Scholar, field-weighted citation metrics, benchmarking against other universities, grants and patents, staff league tables, user accounts, editable profiles and network graphs. Later iterations add other UNZA systems (student information, LMS, HR/payroll, staff performance, promotions).

## Source settings

Verified (see `config/sources.yml`): UNZA's ROR ID and OpenAlex institution ID; the IRIM OAI-PMH endpoint, `https://rims.unza.ac.zm/server/oai/request` (IRIMS, DSpace-CRIS, 8,792 records and 258 sets on November 11, 2026); the OJS base URL and the paths of all 15 journals, which all answer OAI-PMH (JPRM's path is `medicine` and ZJE's is `ZAJE`).

Still to be set: ORCID client credentials in the `pipeline` environment, the OpenAlex contact email and API key, and the source for the schools-to-departments seed. journals.unza.zm leaves an intermediate certificate out of its chain, so the OJS connector adds it from `config/certs/`; that file can go once the site serves its full chain.

Tasks for each stage are [GitHub issues](https://github.com/DataLab-UNZA/ihub-data-analytics-platform/issues), labelled by layer. Demonstration prompts for stage 1 are in [`DEMO_PROMPTS.md`](DEMO_PROMPTS.md).
