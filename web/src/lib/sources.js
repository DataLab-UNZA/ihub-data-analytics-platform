/**
 * The sources the screens name, in display order, mapped to the source codes the data service
 * uses (`marts.dim_source_system`). Labels follow the UI wording: "Repository", "UNZA journals".
 */
export const SOURCE_LABELS = [
  ['openalex', 'OpenAlex'],
  ['dspace_oai', 'Repository'],
  ['ojs', 'UNZA journals'],
  ['orcid', 'ORCID'],
];

/**
 * Label and count for every displayed source.
 *
 * @param {Array<{code: string}>} known Sources the mart has (`unit_sources.sources`).
 * @param {Record<string, number>|undefined} counts Publications per source code for one unit.
 * @returns {Array<{code: string, label: string, value: number|null}>} `value` is null when the
 *   mart has no such source or no figures for this unit (shown as "–", never as 0).
 */
export function sourceCounts(known, counts) {
  const codes = new Set((known ?? []).map((source) => source.code));
  return SOURCE_LABELS.map(([code, label]) => ({
    code,
    label,
    value: counts && codes.has(code) ? (counts[code] ?? 0) : null,
  }));
}
