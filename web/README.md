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
profile, data quality, reports, dashboards, notifications, add-source wizard, and the administration screens other
than Users & roles. They need sources the platform does not have yet (HR and staff data, reviewer decisions).

Wired to the sign-in service: sign-in (Google or an email code), the code screen, sign-out, the user and role in the
top bar, the menu, and Users & roles (real accounts, role and status changes).

The **unit** filter is listed but not applied to the data yet.

## Sign-in and roles (ADR-010)

The browser never holds a token. This server is a backend-for-frontend: route handlers under `src/app/auth/` run the
sign-in flows against the API and keep its tokens in httpOnly cookies.

```
/login ── Continue with Google ─► /auth/google ── API: /api/auth/google/start ─► Google
                                  /auth/google/callback ◄── code + state ── Google
                                    └─ API: /api/auth/google/callback (checks state, PKCE, ID token) ─► cookies
       ── Email me a code ─────► /auth/email ── API: /api/auth/email/request ─► email with 6 digits
/verify-code ── 6 digits ──────► /auth/email/verify ── API: /api/auth/email/verify ─► cookies
```

| Cookie | Holds | Lifetime |
|---|---|---|
| `ihub_at` | access token (JWT) | 15 minutes |
| `ihub_rt` | refresh token (opaque, rotated on use) | 7 days, session at most 30 |
| `ihub_oauth` | signed Google flow state, path `/auth/google` only | 10 minutes |
| `ihub_pending` | the address waiting for its code | 10 minutes |
| `ihub_flash` | a one-off message for the next screen | 1 minute |

All are httpOnly and `SameSite=Lax`, and `Secure` over HTTPS. Form posts also check the `Origin` header.

- `src/proxy.js` runs before every page: signed-out visitors go to `/login?next=…`; an expired access token is refreshed
  silently with the refresh token (the new cookies reach the page in the same request).
- `src/lib/api.js` sends `Authorization: Bearer <access token>` on every API call and sends a 401 to `/login`.
- Roles: the menu (`config/navigation.js`, `permission`), the CSV export button and the admin pages
  (`app/(app)/admin/layout.js`) follow the user's permissions. The API enforces the same rules on every request.
- `IHUB_REQUIRE_SIGN_IN=false` switches sign-in off (production does this until the user store exists, ADR-009).

Run locally with sign-in: set the `IHUB_*` sign-in values in the repository's `.env` (see `.env.example`), start the
API, then `npm run build && npx next start -p 3100` (or `npm run dev -- -p 3100`), and open http://localhost:3100.
`IHUB_PUBLIC_URL` must match that address, and Google must list `<that address>/auth/google/callback` as an
authorised redirect URI. End-to-end check: `scripts/e2e_sign_in.sh` (instructions at its top).

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
- Unit heads see every unit; limiting them to their own unit needs a later ADR.
