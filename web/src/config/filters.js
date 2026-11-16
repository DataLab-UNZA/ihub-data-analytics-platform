/**
 * Global filters. Every signed-in screen shares these four filters; the period
 * filter is also exposed in the top bar. Options are [value, label].
 *
 * The values below are the fallback used when the data service is unreachable.
 * When it is reachable, the real options (years, publication types, schools)
 * replace them (see lib/shell-data.js).
 */
const YEARS = ['2026', '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015'];

export const FILTERS = [
  {
    key: 'period',
    label: 'Period',
    fallback: 'all',
    options: [['all', 'All years'], ...YEARS.map((year) => [year, year])],
  },
  {
    key: 'unit',
    label: 'Unit',
    fallback: 'organisation',
    options: [['organisation', 'Organisation']],
  },
  {
    key: 'source',
    label: 'Source',
    fallback: 'all',
    options: [
      ['all', 'All sources'],
      ['openalex', 'OpenAlex'],
      ['repository', 'Repository'],
      ['journals', 'UNZA journals'],
    ],
  },
  {
    key: 'type',
    label: 'Type',
    fallback: 'all',
    options: [['all', 'All outputs']],
  },
];

export const FILTER_DEFAULTS = Object.fromEntries(FILTERS.map((filter) => [filter.key, filter.fallback]));

/** Filters are kept in a cookie so server components can read them. */
export const FILTER_COOKIE = 'ihub_filters';

/** Source filter values mapped to the source names the API expects. */
export const SOURCE_NAMES = { openalex: 'OpenAlex', repository: 'Repository', journals: 'OJS' };

/** Replaces the options of each filter with `overrides[key]` where one is given. */
export function withOptions(overrides) {
  return FILTERS.map((filter) => (overrides?.[filter.key] ? { ...filter, options: overrides[filter.key] } : filter));
}

export function optionLabel(definitions, key, value) {
  const filter = definitions.find((item) => item.key === key);
  const option = filter?.options.find(([optionValue]) => optionValue === value);
  return option ? option[1] : value;
}
