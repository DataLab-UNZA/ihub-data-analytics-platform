/**
 * Helpers for the ready-made charts of Explore (the catalogue comes from /api/explore/guides).
 * Pure functions, shared by the server pages and the client components.
 */
import { countryName } from '@/lib/countries';
import { formatValue, splitColumns } from '@/lib/viz';

/** The simple filters a visitor can set on a ready-made chart, and their form values. */
export const EMPTY_FILTERS = Object.freeze({ from: '', to: '', type: '', school: '' });

/**
 * The query for a guide under the visitor's simple filters.
 *
 * @param {object} guide A guide from the catalogue.
 * @param {object} filters { from, to, type, school }, each '' for "no restriction".
 */
export function guideSpec(guide, filters = EMPTY_FILTERS) {
  const spec = { ...guide.spec, filters: [...(guide.spec.filters ?? [])] };
  const offered = new Set(guide.filters);
  if (offered.has('years') && filters.from) spec.year_from = Number(filters.from);
  if (offered.has('years') && filters.to) spec.year_to = Number(filters.to);
  if (offered.has('type') && filters.type) spec.filters.push({ column: 'publication_type', op: '==', value: filters.type });
  if (offered.has('school') && filters.school) spec.filters.push({ column: 'school', op: '==', value: filters.school });
  return spec;
}

/** Filters read from a URL's search parameters (only the known keys, as strings). */
export function filtersFromParams(params) {
  const first = (value) => (Array.isArray(value) ? value[0] : value) ?? '';
  return {
    from: /^\d{4}$/.test(first(params.from)) ? first(params.from) : '',
    to: /^\d{4}$/.test(first(params.to)) ? first(params.to) : '',
    type: first(params.type),
    school: first(params.school),
  };
}

/** The URL search string for a set of filters (empty values left out). */
export function filtersToParams(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return params.toString();
}

const text = (value, format) => formatValue(value, format, { full: true });

/**
 * One or two plain sentences about what stands out in a result, for people who do not read
 * charts for a living. Returns [] when there is nothing sensible to say.
 */
export function takeaways(viz, result) {
  if (!result?.rows?.length) return [];
  const { dims, metrics } = splitColumns(result);
  if (!metrics.length) return [];

  // One bar per metric (for example, the share of records with each field).
  if (!dims.length) {
    const row = result.rows[0];
    const items = metrics.map((m) => ({ name: m.label, value: row[m.index], format: m.format })).filter((item) => item.value !== null);
    if (items.length < 2) return [];
    const sorted = [...items].sort((a, b) => b.value - a.value);
    return [`Highest: ${sorted[0].name} (${text(sorted[0].value, sorted[0].format)}). Lowest: ${sorted.at(-1).name} (${text(sorted.at(-1).value, sorted.at(-1).format)}).`];
  }
  if (dims.length !== 1 || viz === 'scatter') return [];

  const [dim] = dims;
  const metric = metrics[0];
  const rows = result.rows.filter((row) => row[metric.index] !== null && row[metric.index] !== undefined);
  if (rows.length < 2) return [];
  const name = (row) => {
    const value = row[dim.index];
    if (value === null) return 'Unknown';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (dim.label === 'Country') return countryName(value);
    return String(value).charAt(0).toUpperCase() + String(value).slice(1);
  };
  const peak = rows.reduce((a, b) => (b[metric.index] > a[metric.index] ? b : a));
  const low = rows.reduce((a, b) => (b[metric.index] < a[metric.index] ? b : a));

  if (dim.type === 'year') {
    const ordered = [...rows].sort((a, b) => a[dim.index] - b[dim.index]);
    if (metric.label === 'Change on previous year') {
      const grew = ordered.filter((row) => row[metric.index] > 0).length;
      return [`Output grew in ${grew} of ${ordered.length} years, each compared with the year before. Very large percentages in early years come from very small numbers.`];
    }
    const latest = ordered.at(-1);
    const incomplete = latest[dim.index] >= new Date().getFullYear() ? ` ${latest[dim.index]} is not complete yet, so a low value there is not a real fall.` : '';
    return [`Highest: ${name(peak)} (${text(peak[metric.index], metric.format)}).${incomplete}`];
  }
  if (metric.format === 'percent' || metric.format === 'decimal') {
    return [`Highest: ${name(peak)} (${text(peak[metric.index], metric.format)}). Lowest: ${name(low)} (${text(low[metric.index], metric.format)}).`];
  }
  const total = rows.reduce((sum, row) => sum + row[metric.index], 0);
  const share = total ? ` (${Math.round((peak[metric.index] / total) * 100)}% of the total shown)` : '';
  return [`Largest: ${name(peak)}, ${text(peak[metric.index], metric.format)}${share}.`];
}
