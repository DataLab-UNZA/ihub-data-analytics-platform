import { apiGet } from '@/lib/api';
import { capitalise } from '@/lib/format';
import { publicationParams } from '@/lib/filters-server';
import { SOURCE_LABELS } from '@/lib/sources';

export const PAGE_SIZE = 10;

const first = (value) => (Array.isArray(value) ? value[0] : value);

/** Query values from the toolbar form, read from the URL (strings only). */
export function readToolbar(searchParams) {
  const page = Number.parseInt(first(searchParams.page) ?? '1', 10);
  return {
    q: (first(searchParams.q) ?? '').trim(),
    oa: first(searchParams.oa) ?? '',
    repository: first(searchParams.repository) ?? '',
    unit: (first(searchParams.unit) ?? '').trim(),
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

/** Value of `toolbar.unit` that shows every unit even when the Unit filter names one. */
export const ALL_UNITS = 'all';

/**
 * The unit a list is scoped to, or '' for every unit. A unit in the URL (a "View publications"
 * link) wins over the Unit filter; one the data service does not know (a stale cookie) is ignored.
 */
export function resolveUnit(filters, toolbar, knownUnits) {
  const wanted = toolbar.unit === ALL_UNITS ? '' : toolbar.unit || publicationParams(filters).unit || '';
  return knownUnits.includes(wanted) ? wanted : '';
}

/** API parameters for the publication list, export or breakdown: global filters plus the toolbar. */
export function buildQuery(filters, toolbar, unit = '') {
  const params = { ...publicationParams(filters) };
  if (unit) params.unit = unit;
  else delete params.unit;
  if (toolbar.q) params.q = toolbar.q;
  if (toolbar.oa) params.oa_status = toolbar.oa;
  if (toolbar.repository === 'in') params.source = 'Repository';
  return params;
}

/** Page URL for the same search on another page. */
export function pageHref(toolbar, page) {
  const query = new URLSearchParams();
  if (toolbar.q) query.set('q', toolbar.q);
  if (toolbar.oa) query.set('oa', toolbar.oa);
  if (toolbar.repository) query.set('repository', toolbar.repository);
  if (toolbar.unit) query.set('unit', toolbar.unit);
  if (page > 1) query.set('page', String(page));
  const text = query.toString();
  return text ? `/publications?${text}` : '/publications';
}

/** Page numbers to show around the current page, with "…" for gaps. */
export function pageWindow(page, pages) {
  const wanted = new Set([1, page - 1, page, page + 1, pages]);
  const numbers = [...wanted].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const result = [];
  numbers.forEach((n, index) => {
    if (index > 0 && n - numbers[index - 1] > 1) result.push('…');
    result.push(n);
  });
  return result;
}

/** Types and sources of the publications behind a list, shaped for <CountList>. */
function breakdownView(breakdown) {
  const order = SOURCE_LABELS.map(([code]) => code);
  const names = Object.fromEntries(SOURCE_LABELS);
  const rank = (code) => (order.includes(code) ? order.indexOf(code) : order.length);
  const sources = [...breakdown.sources]
    .sort((x, y) => rank(x.code) - rank(y.code))
    .map((source) => ({ label: names[source.code] ?? source.name, value: source.publications }));
  return { types: breakdown.types.map((item) => ({ label: item.type, value: item.publications })), sources };
}

/**
 * Loads one page of publications and their type and source breakdown. The list, the count, the
 * breakdown and the CSV export all use `query`, so they always describe the same publications.
 */
export async function loadPublications(filters, toolbar) {
  const options = await apiGet('/api/filters');
  const unit = resolveUnit(filters, toolbar, options.schools);
  const query = buildQuery(filters, toolbar, unit);
  const [list, breakdown] = await Promise.all([
    apiGet('/api/publications', { ...query, page: toolbar.page, page_size: PAGE_SIZE }),
    apiGet('/api/publications-breakdown', query),
  ]);
  return {
    ...list,
    unit,
    query,
    breakdown: breakdownView(breakdown),
    oaOptions: [['', 'OA: All'], ...options.oa_statuses.map((status) => [status, `OA: ${capitalise(status)}`])],
  };
}

/** Rows shaped for <DataTable>. */
export function toTableRows(rows) {
  return rows.map((row) => ({
    id: row.publication_key,
    key: row.publication_key,
    title: row.title,
    year: String(row.year),
    type: row.type,
    oa: capitalise(row.oa_status),
    sources: row.sources,
  }));
}
