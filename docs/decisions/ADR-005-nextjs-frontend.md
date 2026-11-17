# ADR-005: Next.js front end for the signed-in application

- **Status:** Accepted (with [ADR-007](ADR-007-nextjs-only-front-end.md))
- **Date:** November 16, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

The supplied designs cover 43 screens: authentication, an executive overview, organisation and member pages, a publications explorer, source and data-quality administration, reports and settings. They share one shell (sidebar, top bar, global filters), one theme and a small set of repeated blocks (cards, key figures, tables, bar lists, charts).

A first prototype in plain HTML, CSS and JavaScript reproduced every screen, but it repeats markup across 44 files and shares behaviour through data attributes. Adding a screen or changing a block means editing many files.

`CLAUDE.md` describes a Streamlit app in `src/ihub/app/`. This ADR does not replace it. It records the front end for the designed screens, which will be fed by an API once one exists.

## Decision

1. **Next.js (App Router) with React, in JavaScript.** Components are `.js` files containing JSX. There is no TypeScript. A `jsconfig.json` provides the `@/` import alias.
2. **One global stylesheet** (`web/src/styles/global.css`) keeps the theme in one place, as before. Class names follow BEM. There is no CSS-in-JS and no utility framework.
3. **Route groups separate the two frames.** `(auth)` holds the authentication frame; `(app)` holds the signed-in shell. The index, foundations page and 404 sit at the root.
4. **A screen registry is the single source of truth** (`src/config/screens.js`): path, active navigation item, role, refresh date and filter presets. The shell reads it; the screen index is generated from it.
5. **Server components by default.** A component is a client component only when it needs state, effects or browser APIs: the shell, global filters, organisation tree, notification tabs, one-time-code input, countdowns, password rules, CSV export and the two admin editors. Charts are server-rendered SVG with an accessible data table.
6. **Content lives in `src/data/`, not in pages.** Pages map data to components, so swapping mock data for API calls changes one layer.
7. **Shared filters** use a React context backed by `localStorage` through `useSyncExternalStore`, so there is no hydration mismatch.
8. **Next.js conventions for states.** `loading.js` and `error.js` under `overview/`, `not-found.js` at the root, and `metadata` exports for page titles. Preview routes render the same components so every state stays viewable.
9. **Fonts** load through `next/font`, so they are self-hosted.
10. **Quality gates:** `npm run lint` and `npm run build` must pass.

## Consequences

- Repeated blocks (card, key figure, table, bar list, chart, shell) are defined once and reused, so a change to one is made once. The page files total about 2,400 lines, against about 3,250 lines of HTML in the prototype, and content now sits in separate data modules.
- The project needs Node 20.9 or later and a build step, which the Python-only stack did not.
- Pages use mock data. Authentication, exports other than CSV, and every form submission are interface states until an API exists.
- Public deployment of the research front end needs an access-control decision before any sensitive source (students, HR, payroll) is shown, as `CLAUDE.md` already requires.
- The plain HTML prototype has been removed; the Next.js app in `web/` replaces it.

## Alternatives considered

- **Keep plain HTML.** Simple to host, but the duplication is the problem this ADR solves.
- **Pages Router.** Mature, but layouts, loading and error states and metadata are first-class in the App Router.
- **TypeScript.** Safer, but the team asked for JavaScript with JSX; types can be added later per file.
