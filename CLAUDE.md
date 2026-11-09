# CLAUDE.md: iHub Data Analytics Platform

## Project context

A prototype analytics platform for Zambian universities, using the University of Zambia (UNZA) as the case study. It is built by Lighton Phiri (supervisor) and four student collaborators in mob-programming sessions.

- **Iteration 1:** research information only, from OpenAlex, ORCID, the UNZA Institutional Repository (DSpace, via OAI-PMH) and UNZA's OJS journal platform (15 journals, via OAI-PMH and the OJS REST API).
- **Out of scope:** Google Scholar (no official API).
- **Later iterations:** student information systems, LMS, HR/payroll, staff performance and promotions. New sources must be addable without changing existing ones.

### What iteration 1 shows

Copy these patterns from SciVal, Dimensions, OpenAlex and Pure/VIVO:
- entity pages (UNZA overview, School, Department, Author, Journal)
- a publications explorer with filters (year, type, OA status, department, source, venue), CSV export and links to the DOI, repository or OJS record
- one global year filter applied to all charts
- simple trends: output per year, OA share, top venues and collaborating countries/institutions
- a source coverage page, e.g. publications in OpenAlex but missing from the repository

Leave these out: field-weighted citation metrics, benchmarking against other universities, grants and patents, individual staff rankings and h-index league tables, user accounts, editable profiles and network graphs.

## Architecture

```
sources -> connectors (Python) -> raw -> staging -> intermediate -> marts -> Streamlit app
                                  \___________ DuckDB, built by dbt ___________/
```

- **Connectors** (`src/ihub/connectors/`): each subclasses `Connector` in `base.py` and only fetches. They never clean data.
- **raw:** records exactly as fetched (JSON Lines, then the DuckDB `raw` schema), with source name and fetch time.
- **staging** (`transform/models/staging/<source>/`): one folder per source. Rename, type-cast, standardise. No joins across sources.
- **intermediate** (`transform/models/intermediate/`): cross-source matching and de-duplication. Publications match on DOI first, then normalised title + year + first-author surname. Authors match on ORCID first, then OpenAlex ID.
- **marts** (`transform/models/marts/research/`): the research star schema.
- **App** (`src/ihub/app/`): Streamlit pages. Pages never contain SQL; they call functions in `src/ihub/mart/`.
- **Pipeline:** a scheduled GitHub Action runs the connectors and `dbt build`, then publishes `ihub.duckdb` as a GitHub Release asset.
- **Deployment:** a Docker image with the DuckDB file built in, deployed to Google Cloud Run. Auth uses Workload Identity Federation, so there are no service-account keys.

### Research mart (star schema)

- `fact_publication`: one row per de-duplicated publication. Keys: publication, venue, year, type. Measures: cited_by_count, n_authors, n_unza_authors, is_oa, oa_status, is_international_collab, in_openalex, in_repository, in_ojs.
- `fact_authorship`: one row per publication × author × affiliation. Keys: publication, author, org, year. Also author_position and is_corresponding.
- `dim_publication`, `dim_author`, `dim_org` (one hierarchy: institution > school > department, from the `unza_org_units` seed), `dim_venue`, `dim_year`, `dim_publication_type`, `dim_topic` + `bridge_publication_topic`, `dim_source_system` + `bridge_publication_source`.
- Department attribution draws on ORCID employment records, DSpace community/collection names and affiliation strings, mapped through the `department_aliases` seed. Publications that cannot be mapped go to "Unassigned department".

## Conventions

- Python 3.12, managed with **uv**. Add dependencies with `uv add <pkg>` (or `uv add --group dev <pkg>`). Never hand-edit `uv.lock`.
- **ruff** handles both linting and formatting. Code must pass `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest` before a PR.
- Type hints on all public functions. Docstrings on modules and public classes.
- British English in docs, UI text and comments.
- dbt model names: `stg_<source>__<entity>`, `int_<entity>__<purpose>`, `fact_<name>`, `dim_<name>`, `bridge_<a>_<b>`.
- Every new connector gets a pytest test that uses recorded sample responses. Tests never call live APIs.
- **No secrets in the repository, ever.** API keys go in `.env` locally and in the GitHub `pipeline` environment (secrets restricted to `main`) for Actions. Every variable name must be listed in `.env.example`. No data files or `.duckdb` files are committed.
- Architecture changes get a short ADR in `docs/decisions/` (`ADR-NNN-title.md`).
- Research metadata may be public. Future sensitive sources (students, HR, payroll) must never be published as release assets or printed in public workflow logs. They need private storage and access control, recorded in an ADR before any work starts.
- `main` is protected: changes go through pull requests only, and CI must pass. No approving review is enforced, but every pull request should be reviewed by a teammate before it is merged (Lighton may merge his own).
- Students work on their own with Claude's free plan through the context pack (`scripts/make_context_pack.py`, published on the `context-pack` release by `.github/workflows/context-pack.yml`). See `docs/STUDENT_GUIDE.md` and `docs/STUDENT_PROMPTS.md`.

## Mob-session and commit rules

- The team logs every prompt in the Google Sheet "misc-ihub26-data_analytics_platform - Mob Programming Prompt Log" (https://docs.google.com/spreadsheets/d/1ooq0gLL_xibZTCReVdlqsvwWDoj4w845mdiLpWOQeiQ/edit). Use the Google Sheets connector to read and update it.
  - Tab "Prompt Log": A Session, B Date, C Time, D Navigator, E Reviewer, F Prompt (exact wording), G Outcome (Worked / Revised / Undone), H Commit hash, I Notes, J Co-authored-by trailer (auto), K Reviewed-by trailer (auto). Row 2 is an example; real entries start at row 3.
  - Tab "Team": A Full name, B GitHub username, C Commit email (GitHub no-reply), D Role.
- When I say "run row N", read the prompt in column F of that row and carry it out exactly as written.
- These commit rules apply to mob sessions and to sessions on Lighton's account. **When a student works on their own**, the student is the commit author (their name and email from the Team tab, set with `git config`); add a `Co-authored-by` line, copied from the Team tab, only for a teammate who paired with them.
- When I ask you to commit:
  1. Read the Prompt Log rows that have an Outcome of Worked or Revised and an empty Commit hash. These are the prompts covered by this commit.
  2. Write the commit message: a short imperative summary line; a body explaining what changed and why; a line "Prompt log: Session <A>, row(s) <numbers>"; then, at the end, the exact text from column J of each of those rows (one line per distinct Navigator) and from column K (one line per distinct Reviewer). Copy the trailers exactly; never type names or emails yourself.
  3. If column J or K shows "not in Team tab" or "Email missing in Team tab", stop and tell me instead of committing.
  4. The commit author is the "Lighton Phiri" row of the Team tab (name from column A, email from column C). If that email is empty, stop and ask me.
  5. After pushing, write the short commit hash into column H of every row included in the commit.
- Never mention Claude anywhere in commits or pull requests: no co-author line, no session link.

## Guided answers and commit credit

- **Offer choices, not open questions.** Students often work on Claude's free plan, where every message counts. Whenever a decision is needed, give 2 to 4 numbered options, one line each with the trade-off, mark the recommended one, and wait for the number.
- **Ask whose change it is before every important commit.** Whoever is typing (Lighton or a student), ask "Whose change is this?" with numbered options taken from the Team tab (Bruce Mainza, Mubanga Chibesa, Chilandu Phiri, Joshua Mvula, Lighton Phiri), and ask who reviewed it. Use the matching Prompt Log rows (or, outside a logged mob session, the Team tab) for the Co-authored-by and Reviewed-by trailers, so the commit is credited to the right student.
- **Free-plan limits.** If a student's usage is running out, tell them to push their branch and email Lighton Phiri (lighton.phiri@unza.ac.zm) with the subject "iHub: please run on Max", the branch name and the next prompt.
- The roadmap is in `docs/ROADMAP.md`. Until the mid-point review, nobody owns a part of the system.

("I" and "me" in these rules refer to Lighton Phiri.)
