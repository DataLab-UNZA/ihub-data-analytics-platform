# ADR-007: Next.js is the only front end; the Streamlit app is retired

- **Status:** Proposed
- **Date:** November 16, 2026
- **Decided by:** the team, agreed with Lighton Phiri; for review by Lighton Phiri

## Context

[ADR-005](ADR-005-nextjs-frontend.md) added a Next.js front end in `web/`, and [ADR-006](ADR-006-research-api-for-the-web-front-end.md) added a read-only FastAPI service, `ihub.api`. Both read the research mart through `ihub.mart`. ADR-006 kept the Streamlit app and left the choice of front end to the team.

Running two front ends over the same data doubles the work for every screen, splits testing, and leaves users unsure which one is current. The designed screens, the planned staff sign-in and the per-role views fit Next.js. Streamlit could not provide them without workarounds.

The team has chosen Next.js as the only front end.

## Decision

1. **The Streamlit app is removed.** This covers `src/ihub/app/`, `.streamlit/`, its tests, and the `streamlit` and `plotly` dependencies. The idle-pause workaround described in [ADR-002](ADR-002-hosting.md) goes too: Next.js keeps no connection open between requests, so Cloud Run can scale to zero without it.
2. **Next.js (`web/`) is the only user interface.** Pages never contain SQL. They call `web/src/services/*`, which calls the API.
3. **FastAPI (`ihub.api`) is the serving backend.** It handles research data, and later users and authorisation ([ADR-008](ADR-008-staff-sign-in-with-google.md), [ADR-009](ADR-009-user-store-and-staff-data.md)). Routes stay thin and call `ihub.mart`, which keeps all the SQL. Connectors and dbt stay as the weekly batch pipeline.
4. **One Cloud Run service with two containers.** The Next.js container receives traffic on port 8080. The API runs as a sidecar on `localhost:8000` and is never exposed publicly. The service still scales to zero, and the DuckDB file is still built into the API image.
5. **Order of work.** First switch the deployment to Next.js plus the API, so the live service never goes down. Then delete the Streamlit code and update `CLAUDE.md`, `README.md` and the docs.

## Consequences

- One front end and one query path. A business rule changes once, in `ihub.mart`.
- The deploy builds two images, and CI gains a `web` job (`npm ci`, `npm run lint`, `npm run build`).
- The two containers need 1 GiB of memory between them, which is more than Streamlit used. The free tier allowances in ADR-002 still apply.
- Students need Node 20.9 or later as well as Python and uv.
- The parts of [ADR-001](ADR-001-technology-stack.md) (web interface) and ADR-002 (idle pause) that are about Streamlit are superseded. ADR-005 and ADR-006 become Accepted when this ADR is.
- Until staff sign-in exists, the mock sign-in screens and the "not connected yet" administration screens are hidden in production.

## Alternatives considered

- **Keep both front ends.** No migration work, but every feature would be built twice.
- **Keep Streamlit only.** Pure Python, but it cannot deliver the designed screens or proper sign-in.
- **Two Cloud Run services (web and API).** The API would need its own public address, plus service-to-service authentication. A sidecar keeps the API private with nothing extra to configure.
