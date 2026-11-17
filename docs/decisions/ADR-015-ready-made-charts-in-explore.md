# ADR-015: Ready-made charts in Explore

- **Status:** Proposed
- **Date:** November 17, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

Explore was a general chart builder (dataset, metrics, group-by, filters, chart type). It can draw almost anything, but a non-technical user has to know what to ask for. The team asked for the same power in a form that is easy to use, with a set of questions UNZA managers actually ask: output and growth, impact, open access, collaboration, researchers, topics, venues, and data quality.

## Decision

1. **A catalogue of ready-made charts ("guides") answers plain questions.** Each guide has a title, a question, a chart type, a short "how to read this chart" and a query. The catalogue is Python data in `ihub.mart.explore_guides` (no SQL), served by `GET /api/explore/guides`. Explore now opens on a gallery of guides grouped by theme, with a search box; the chart builder is one click away ("Build your own chart", and "Change it in the chart builder" on every guide).
2. **A guide is a query for the existing semantic layer, not a special case.** So it can be run, downloaded as CSV, saved, added to a dashboard and opened in the builder like any other chart. Where the semantic layer lacked something, it was extended rather than bypassed:
   - new columns and metrics (decade, citation bands, team-size bands, medians and quartiles, completeness shares, source combinations);
   - new datasets for schools, authorships by school, researchers by school, output per researcher, topics by school and school-to-school co-authorship;
   - `transform` on a query: `rolling3` (3-year average), `yoy` (change on the previous year) and `cumulative_share` (Pareto);
   - `sort_expr` on a column, so bands such as "2-4" come before "10-19";
   - three chart types: bars and line, bubble chart, sunburst; and chart options for 100% stacking and a logarithmic scale.
3. **School charts use the same credit as the Organisation screen.** What only Python knows (roster-based school credit, [ADR-012](ADR-012-school-output-from-the-staff-roster.md), and the hand-confirmed links of [ADR-014](ADR-014-members-directory-from-the-staff-roster.md)) reaches SQL as two temporary tables, `unit_pub (school, publication_key)` and `author_unit (author_key, school)`, loaded per query by `ihub.api.units.UnitScope.chart_tables` and cached until the database or roster changes. Without a roster the department-based schools are used. Publications with no credited school are left out of school charts. Only keys and school names enter the tables: no author name or staff ID.
4. **No individuals are named or ranked.** Researcher charts count authors (roles, ORCID use, publications per researcher as bands); "most cited" ranks publications, not people. This keeps to the rule in `CLAUDE.md` against individual rankings.
5. **Simple filters, worked out per guide.** A guide offers years, kind of publication and school only where its data has them and the chart is not already split by them. The data-quality theme is shown only to users who can manage sources or review quality.
6. **Plain language.** Each guide explains how to read it and, from the result, says what stands out (the highest value, whether a recent year is incomplete). The builder's labels were reworded ("What to measure", "Break down by", "Only include").

## Consequences

- Every guide is run against the tiny test mart, with and without a roster, in `tests/test_explore_guides.py`, so a broken guide fails the build.
- School charts cost one extra step per query (about 0.2 seconds with roster credit cached).
- Some figures need care: a guide that groups by school counts a publication once in each school credited with it, and recent years are incomplete. Both are said on the guide.
- Saved charts created in the builder are unchanged; `/explore?chart=<id>` still opens them for editing.

## Alternatives considered

- **Hard-code each chart's data in Python and draw it in the front end.** Rejected: such charts could not be saved to dashboards, exported or edited, and the logic would be duplicated.
- **Put the school credit into the mart.** Rejected for the same reason as in ADR-012: the mart is public and the roster is private.
- **A wizard that asks questions and picks a chart.** Considered; a gallery of questions is simpler to scan and to extend.
