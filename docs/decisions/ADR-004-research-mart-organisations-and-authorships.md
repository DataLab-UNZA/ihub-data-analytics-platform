# ADR-004: Organisations, authorships and sources in the research mart

- **Status:** Proposed
- **Date:** November 12, 2026
- **Decided by:** (author to add), for review by Lighton Phiri

## Context

Stage 5 completes the research star schema described in `CLAUDE.md`. Building it showed that the schema, as written, could not answer some of the questions the planned pages ask.

1. **`dim_org` was defined as UNZA's hierarchy only**, but `fact_authorship` has an organisation key and the trends ask for collaborating countries and institutions. Those institutions are not UNZA units.
2. **Authors from the repository (IRIMS) and OJS are name-only.** They cannot be matched to OpenAlex or ORCID authors (issue #19), so using every source's authorships would count one person more than once.
3. **Only OpenAlex gives affiliations.** `n_unza_authors` and `is_international_collab` can be worked out only where OpenAlex gives them.
4. **A department is evidence of three different kinds** (OpenAlex affiliation text, ORCID employments, IRIMS community and collection names), of which only the first two name an author. ADR-003 fixed how a name is matched; it did not say how the result reaches the facts.
5. **OJS gives no venue ID**, so every OJS article fell into "Unknown venue" and the Journal pages would have had nothing to show.

## Decision

1. **`dim_org` holds three kinds of row**, told apart by `org_kind`:
   - `unza_unit`: the hierarchy institution > school > department from the `unza_org_units` seed, plus an "Unassigned department" row under the institution;
   - `external`: every other institution OpenAlex lists on an authorship, with its `country_code`, `org_type` and ROR. External rows have no parent;
   - `unknown`: one "Unknown organisation" row for authors with no affiliation.
   `dim_org` also carries `school_name` and `country_code` (ZM for UNZA units).
2. **`fact_authorship` has one row per publication × author × organisation**, with keys for publication, author, org and year, plus `author_position`, `is_corresponding` and `org_basis` (the rule that produced the row). Count authors with `count(distinct author_key)`.
3. **Which authorships are used.** OpenAlex's authorships, plus the name-only authors of the repository and OJS for a publication that has no OpenAlex record. One authorship per publication and author, however many source records carry it.
4. **How an authorship gets its organisations.**
   - An institution other than UNZA that OpenAlex lists gives an `external` row.
   - An author at UNZA gets the department found for that author (OpenAlex affiliation text, an ORCID employment current in the publication's year). Without one, the department found for the publication (IRIMS sets). Without one, "Unassigned department".
   - An author with no institution and no department evidence gets "Unknown organisation".
   - An author is at UNZA when OpenAlex lists UNZA for them, when a department was found for them, or when they are a name-only author of the repository or OJS.
5. **Placeholder rows.** Every publication keeps at least one row at UNZA. When none of its authorships is at UNZA (including a publication with no authors at all), one row with the "No author listed" author in `dim_author` carries the department found for the publication, or "Unassigned department".
6. **Department matching** follows ADR-003 and adds:
   - affiliation text is cut at semicolons, then commas, and every run of consecutive parts (up to as many as the longest alias has) is tried as a name, so a department whose name contains commas still matches;
   - when two matches overlap in the same piece of text, only the longest is kept;
   - a name that resolves to a school or to the institution gives context only, never an attribution.
7. **Missing affiliations are unknown, not zero.** `n_unza_authors` (authors whose OpenAlex affiliation is UNZA) and `is_international_collab` (any OpenAlex affiliation outside Zambia) are NULL for a publication with no OpenAlex affiliation.
8. **`dim_source_system` is built from a `source_systems` seed**, and `bridge_publication_source` uses its key instead of the source's name. Adding a source means one seed row, one CTE in `int_publications__source_records` and one entry in `source_priority`; a test fails if the seed row is missing.
9. **Topics come from OpenAlex only**: `dim_topic` (topic, subfield, field, domain on one row) and `bridge_publication_topic`.
10. **OJS journals are venues**, keyed on `ojs:` plus the journal's path. A journal whose citation text does not name it is shown as "OJS journal <path>".
11. **The exclusion of past examination papers is deferred.** ADR-003 says IRIMS holds examination papers next to research outputs and that stage 4 or 5 must exclude them. The names of the IRIMS collections that hold them cannot be listed until real data is loaded, and no name is guessed. The exclusion is done once the set names are known, in `int_publications__source_records`, before de-duplication.

## Consequences

- **Limitation: examination papers are still counted as publications** in every count and chart until decision 11 is done.
- **Limitation: placeholder rows.** The "Unknown organisation" and "No author listed" rows are not real organisations or people. Pages that list authors or organisations must leave them out, or show them as "unknown".
- **Limitation: repository and OJS authors count as UNZA authors** for department attribution, because both are UNZA sources. A co-author from another institution who appears only there gets the item's department.
- **Limitation: `n_unza_authors` counts OpenAlex affiliations only.** An author who is at UNZA according to ORCID employment, the repository or OJS alone does not count, so the number can understate UNZA's authors.
- **NULL means unknown, not none.** For `n_unza_authors` and `is_international_collab`, NULL means OpenAlex gives no affiliation for the publication (repository, OJS and ORCID-only publications, and OpenAlex works without affiliations). Charts and filters must show it as unknown and never count it as 0 or false. Both columns therefore have no not-null test.
- **A person who appears only in repository or OJS records can still appear as more than one author**, as in decision 3 of issue #19.
- **Overlapping matches of equal length are all kept**, so one affiliation text can still give two units. No such pair exists in the seeds on November 12, 2026.
- **None of this has been run on real data.** The department match rate, the number of external institutions and the size of `fact_authorship` are not yet known. The tests use recorded fixtures.
- `CLAUDE.md` is updated to describe `dim_org`, `fact_authorship`, `dim_author` and the NULL measures.

## Alternatives considered

- **A separate `dim_institution`** for external institutions: cleaner, but it adds a table and a second key to `fact_authorship`.
- **Country code only, no external institutions:** simplest, but a "top collaborating institutions" chart would be impossible.
- **All sources' authorships in `fact_authorship`:** the most complete, but it double-counts people who appear in OpenAlex and in the repository.
- **OpenAlex authorships only:** the cleanest, but repository-only and OJS-only publications would have no author or department rows.
- **Using 0 and false when affiliations are missing:** simpler to chart, but it states something we do not know.
- **Excluding examination papers by `dc:type`:** may miss some; the collection names are explicit and can be reviewed.
