import { apiGet } from '@/lib/api';
import { capitalise } from '@/lib/format';
import { publicationParams } from '@/lib/filters-server';

export const PAGE_SIZE = 10;

const first = (value) => (Array.isArray(value) ? value[0] : value);

/** Query values from the toolbar form, read from the URL (strings only). */
export function readToolbar(searchParams) {
  const page = Number.parseInt(first(searchParams.page) ?? '1', 10);
  return {
    q: (first(searchParams.q) ?? '').trim(),
    oa: first(searchParams.oa) ?? '',
    repository: first(searchParams.repository) ?? '',
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

/** API parameters for the publication list or export: global filters plus the toolbar. */
export function buildQuery(filters, toolbar) {
  const params = { ...publicationParams(filters) };
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

export async function loadPublications(filters, toolbar) {
  const [list, options] = await Promise.all([
    apiGet('/api/publications', { ...buildQuery(filters, toolbar), page: toolbar.page, page_size: PAGE_SIZE }),
    apiGet('/api/filters'),
  ]);
  return {
    ...list,
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
