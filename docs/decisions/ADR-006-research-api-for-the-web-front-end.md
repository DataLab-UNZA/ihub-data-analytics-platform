# ADR-006: A read-only research API between the mart and the Next.js front end

- **Status:** Accepted (with [ADR-007](ADR-007-nextjs-only-front-end.md))
- **Date:** November 16, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

[ADR-005](ADR-005-nextjs-frontend.md) added a Next.js front end (`web/`) for the designed screens. Its first version showed illustrative data. The real data is in the DuckDB research mart (`marts.*`), which the Streamlit pages read through `ihub.mart`.

`CLAUDE.md` says pages never contain SQL: they call functions in `src/ihub/mart/`. A Node process reading DuckDB directly would need its own SQL, and two copies of the rules (for example, that an unknown venue is not counted, or that `is_international_collab` is NULL when OpenAlex gives no affiliation) would drift apart.

## Decision

1. **A small FastAPI app, `ihub.api`, wraps `ihub.mart`.** Each route parses its query, calls a mart function and returns JSON. It holds no SQL. It is read-only and opens the database the same way the Streamlit app does (`IHUB_DUCKDB_PATH`).
2. **New questions are new mart functions, not API code.** Topics, schools and units, collaboration, the venue directory and a single publication's detail are in `ihub.mart.insights`, with tests against a hand-built mart.
3. **Next.js calls the API from the server only** (`web/src/lib/api.js`, address in `IHUB_API_URL`). The browser never sees the API address, and the CSV export is proxied through a Next.js route.
4. **Global filters live in a cookie**, so server components can apply the period, source and type filters and re-fetch on change. The same filters persist across screens as the design requires.
5. **Unavailable data is an error state, not zeros.** If the API or mart is down, a screen shows the "couldn't load this data" state. An unknown value is shown as "Unknown", never 0.
6. **Screens with no real source stay illustrative and say so.** Individual members, per-staff measures, data-quality queues, notifications, reports, dashboards and administration show a "not connected yet" label. Per-staff and per-FTE measures stay "Unknown" until an HR source exists.

## Consequences

- One query layer serves both Streamlit and Next.js. Changing a business rule in `ihub.mart` changes both.
- Two processes run in development and in any deployment of the Next.js app: the API and the web server. Deployment is not covered here; the Cloud Run image currently runs Streamlit only.
- The unit filter is listed but is not applied to the data yet: filtering publications by school needs a new mart query.
- School totals count a publication once in each school with an author, so they add up to more than the number of publications. Most publications are "Unassigned department" until the department mapping (ADR-003) improves.
- `ihub.mart.research.PublicationRow` gained an optional `publication_key` so a row can link to its record page.
- The context pack budget in `scripts/make_context_pack.py` rose from 30,000 to 33,000 characters to fit the new modules, and method-less data classes are listed on one line.

## Alternatives considered

- **Read DuckDB from Node** (`@duckdb/node-api`). Fewer processes, but it duplicates the SQL and the data rules.
- **Replace Streamlit with Next.js now.** The Streamlit app is deployed and working; this ADR adds a second front end over the same data and leaves the decision to the team.
- **Filters in the URL.** Shareable, but every internal link would need to carry them. A cookie keeps links clean; shareable views can be added later.
