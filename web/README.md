# iHub Analytics: web front end

Next.js (App Router) with React, written in JavaScript (`.js` files containing JSX).
Decision records: [ADR-005](../docs/decisions/ADR-005-nextjs-frontend.md) (Next.js) and [ADR-006](../docs/decisions/ADR-006-research-api-for-the-web-front-end.md) (research API).

## Run it

The front end reads real data through the research API (`src/ihub/api`), so start that first.

```
# 1. API (from the repository root). Point it at a database that has the research mart.
IHUB_DUCKDB_PATH=data/real.duckdb uv run uvicorn ihub.api.app:app --port 8000

# 2. Front end
cd web
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
npm run start      # serve the production build
npm run lint
```

Requires Node 20.9 or later. The API address is `IHUB_API_URL` (default `http://127.0.0.1:8000`; see `.env.example`).
Open `/` for an index of every screen, or `/login` to follow the sign-in flow.

## Real data and illustrative data

Wired to the research mart: overview, organisation (schools and units), publications (search, paging, CSV export,
record pages), journals, topics, collaboration, source coverage, data sources and the global filters (period, source,
type). If the API or mart is down, these screens show a "couldn't load this data" state.

Still illustrative, and labelled "not connected yet": School of Medicine page, compare units, members and member
profile, data quality, reports, dashboards, notifications, add-source wizard, administration and the sign-in screens.
They need sources the platform does not have yet (HR and staff data, reviewer decisions, authentication).

The **unit** filter is listed but not applied to the data yet.

## Data flow

```
DuckDB mart -> ihub.mart (SQL lives here) -> ihub.api (FastAPI, JSON) -> src/lib/api.js -> src/services/* -> pages
```

- `src/services/` calls the API and shapes responses for components (formatting, scales, trees). Pages stay thin.
- Global filters are saved in the `ihub_filters` cookie; server components read it with `readFilters()`
  (`src/lib/filters-server.js`) and changing a filter refreshes the route.

## Structure

```
web/
  public/img/                  SVG assets (world map, login backdrop, thumbnails)
  src/
    app/                       routes (App Router)
      layout.js                root layout: fonts, global CSS, metadata
      page.js                  screen index (generated from the registry)
      not-found.js             404, wrapped in the app shell
      foundations/             design-system reference page
      (auth)/                  authentication frame + screens
      (app)/                   signed-in shell + screens
        overview/ organisation/ members/ publications/ ...
    components/
      layout/                  AppShell, Sidebar, Topbar, PageHeader, GlobalFilters, SiteFooter
      ui/                      Card, Kpi, DataTable, BarList, Button, Form, Alert, Chip, Steps ...
      charts/                  LineChart, BoxPlot, StackBar, WorldMap (server-rendered SVG)
      auth/                    AuthPage, LoginScreen, OtpInput, Countdown, CreatePasswordForm
      features/                one folder per area, for components used by a single area
    config/                    navigation, roles, filters and the screen registry
    context/                   FiltersProvider (shared global filters)
    data/                      illustrative content for screens with no real source yet
    services/                  API calls and view-model shaping for the real-data screens
    lib/                       helpers (formatting, CSV export, filter storage)
    styles/global.css          the only stylesheet
```

## Conventions

- **Server components by default.** Add `'use client'` only for state, effects or browser APIs.
- **Pages stay thin.** A page sets `metadata`, renders `<PageHeader>` and composes components with data from `src/data/`.
- **No SQL and no mock numbers on real-data screens.** Fetch through `src/services/`; show "Unknown" for missing values, never 0.
- **One place per concern.** Navigation: `config/navigation.js`. Per-screen role, nav item, refresh date and filter presets: `config/screens.js`. Filter options: `config/filters.js`.
- **One stylesheet.** Add or change styles in `styles/global.css` (BEM names). Use the spacing utilities (`mt-24`, `mb-16`) rather than inline styles. Inline `style` is only for data-driven custom properties such as `--h` or `--x`.
- **Accessible by default.** Every table has a caption, every chart has a data table, every field has a label, and each page has one `<h1>` (from `PageHeader`).
- **No animations or transitions.**
- British English in all text.

## Adding a screen

1. Add an entry to `SCREENS` in `src/config/screens.js` (path, group, title, `nav`, `role`).
2. Create `src/app/(app)/<path>/page.js`: export `metadata`, render `<PageHeader title="…" />`, then your content.
3. Put its content in `src/data/` and any reusable block in `src/components/`.

## Known gaps

- Forms navigate between screens but do not write anything (the API is read-only).
- Excel export needs server-side generation, so that button is disabled. CSV export works.
- A few links (terms of use, help and data definitions, per-field mapping) are placeholders.
- Demo values on the sign-in, code and password screens mirror the designs and should be removed when wired to a back end.
