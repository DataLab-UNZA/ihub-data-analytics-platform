# ADR-003: Shared staging rules and department attribution

- **Status:** Proposed
- **Date:** November 11, 2026
- **Decided by:** Joshua Mvula (issues #17 and #18), for review by Lighton Phiri

## Context

Stage 3 adds staging models for IRIMS (DSpace), OJS and ORCID next to OpenAlex, and the seeds that attribute publications to UNZA's departments. Two problems came up while looking at the real data on November 11, 2026.

1. **The same cleaning rules were about to be written four times.** Every source needs DOIs, titles, names, years and publication types cleaned, and records that arrive more than once reduced to one. Written separately in each model, the rules would drift apart, and cross-source matching (stage 4) compares values that must have been cleaned identically.
2. **Department names are ambiguous.** In 10,628 OpenAlex works, 258 IRIMS communities and collections, and ORCID employments, UNZA's units appear under current names, earlier names ("Biological Sciences", now Biosciences and Biotechnology), spelling variants ("Gynecology", "Paraclinical") and abbreviations ("LSSE"). Some names belong to two units: "Biomedical Sciences" is a department of both Health Sciences and Veterinary Medicine. Worse, a name can mean different units in different sources: the IRIMS community "Medicine" is the School of Medicine, but "Department of Medicine" in an affiliation is Internal Medicine.

## Decision

1. **Shared rules are dbt macros** in `transform/macros/`, and every staging model uses them:
   - `latest_delivery`: one row per record, keeping the newest delivery;
   - `normalise_doi`, `normalise_title`, `clean_text`, `year_from_text`, `name_family`, `name_given`;
   - `standardise_publication_type`, which maps each source's own type (dc:type, ORCID work type) to the OpenAlex vocabulary used by the marts;
   - `department_name_key`, the one key on which department names are compared.

   A rule changes in one place, and every source follows.
2. **One staging model per entity per source.** Examples: `stg_dspace_oai__items`, `__sets`, `__item_sets`, `__item_authors`; `stg_ojs__articles`, `__article_authors`; `stg_orcid__researchers`, `__works`, `__employments`. There are no joins across sources. A source with two payload shapes (OJS over OAI-PMH or the REST API) maps each shape onto the same columns in its own CTE.
3. **The organisation hierarchy and its aliases are seeds.** `unza_org_units` holds institution > school > department (or centre), plus the Library directly under the institution. It comes from the school pages of www.unza.zm. `department_aliases` maps each name seen in the sources to a unit, and each row can be qualified:
   - `applies_to`: the kind of name it is valid for (`any`, `affiliation`, `dspace_set` or `orcid_employment`);
   - `school_context_id`: the alias applies only when that school is also named;
   - `confidence` (`official`, `variant`, `renamed` or `assumed`) and `evidence`, so a reviewer checks only the uncertain rows.
4. **Attribution rule for stage 4.** A name is reduced to its `department_name_key`. The most specific alias row applies: the source's own `applies_to` before `any`, and a row whose school context is satisfied before one without. When a name still points to two units, the publication goes to "Unassigned department" rather than to a guess.
5. **The seeds are tested as data.** Two data tests in `transform/tests/` fail the build if a unit breaks the hierarchy, if a school context does not contain its unit, or if an alias maps to two units in the same context.
6. **Staging models are tables, not views.** On the real data (8,792 IRIMS items with their XML, 1,482 ORCID records, one of them 8.4 MB), views ran out of memory, because every test and downstream model parsed the raw JSON again. Two rules keep the build small. A full build of every source now takes about 20 seconds:
   - `latest_delivery` ranks deliveries on small values (key, fetch time, a payload hash) and reads the winners back by `rowid`, so payloads are never sorted.
   - A JSON array is unnested in a step of its own. Select the list first, then `unnest` it, and never next to the payload: DuckDB copies every other selected column onto each unnested row.

## Consequences

- Adding a source means writing its staging models with the existing macros, then adding one CTE to `int_publications__source_records` (stage 4).
- Renaming a department, or finding a new spelling, is a one-line change to `department_aliases.csv`, with no code change.
- Rows marked `assumed` (for example Soil Science, assumed to be Land Management) are attributed now, but are listed for Lighton to confirm.
- On November 11, 2026 the aliases resolved 81% of the department names in UNZA employments on ORCID (663 of 820). They also resolved every IRIMS community and collection named after a school, department, centre, institute or directorate in the seed. The IRIMS sets left unmatched are past examination papers, CRIS entities, other institutions, research-theme collections ("Governance Research") and service units that the seed leaves out (CICT, TDAU, the UNZA Press, the UNZA Clinic).
- IRIMS holds past examination papers next to research outputs. Staging keeps them, because it never filters. Stage 4 or 5 must exclude them, for example by their collections, or they will be counted as publications.
- The seeds reflect the university website on November 11, 2026. When UNZA restructures, the seed is edited and the old names become `renamed` aliases.

## Alternatives considered

- **Cleaning in Python, in the connectors:** rejected. Connectors only fetch (CLAUDE.md), and the raw layer must stay exactly as fetched.
- **One alias per name, with no qualifiers:** simpler, but it would attribute every "Biomedical Sciences" paper to one school and every IRIMS "Medicine" item to Internal Medicine.
- **Fuzzy matching of department names:** it finds more matches, but it guesses silently and is hard to review. An explicit alias table can be reviewed, tested and corrected.
