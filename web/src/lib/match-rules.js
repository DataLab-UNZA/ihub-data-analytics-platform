/**
 * Plain-language descriptions of the pipeline's match rules (CLAUDE.md, "intermediate":
 * publications match on DOI first, then normalised title + year + first-author surname).
 */
const RULES = {
  doi: 'Matched on a shared DOI.',
  title_year: 'Matched on the normalised title, publication year and first-author surname (no shared DOI).',
  title_year_to_doi: 'Matched on title, year and first-author surname, then joined to a record that has a DOI.',
  single_record: 'The only record found for this publication, so there was nothing to match.',
};

export function describeMatchRule(rule) {
  return RULES[rule] ?? (rule ? `Match rule: ${rule}.` : 'No match rule recorded.');
}
