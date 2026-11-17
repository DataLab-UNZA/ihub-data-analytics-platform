import { notFound, redirect } from 'next/navigation';
import { ApiError, apiGet } from '@/lib/api';
import { publicationParams } from '@/lib/filters-server';
import { capitalise } from '@/lib/format';

export const PAGE_SIZE = 20;

const first = (value) => (Array.isArray(value) ? value[0] : value);

/** Query values from the directory's search form, read from the URL (strings only). */
export function readMemberQuery(searchParams) {
  const page = Number.parseInt(first(searchParams.page) ?? '1', 10);
  const orcid = first(searchParams.orcid) ?? '';
  return {
    q: (first(searchParams.q) ?? '').trim(),
    orcid: ['linked', 'unknown'].includes(orcid) ? orcid : '',
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

/** Directory URL for the same search on another page. */
export function memberPageHref(query, page) {
  const params = new URLSearchParams();
  if (query.q) params.set('q', query.q);
  if (query.orcid) params.set('orcid', query.orcid);
  if (page > 1) params.set('page', String(page));
  const text = params.toString();
  return text ? `/members?${text}` : '/members';
}

/** Calls the members API. Named people need `members:read`, so a 403 shows the restricted page. */
async function members(path, params) {
  try {
    return await apiGet(path, params);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) redirect('/access-restricted');
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

/**
 * One page of the directory, A to Z. All four global filters apply (period, unit, source, type),
 * the same way as on the publication list: `publicationParams` is the shared mapping.
 */
export async function loadMembers(filters, query) {
  return members('/api/members', {
    ...publicationParams(filters),
    q: query.q,
    orcid: query.orcid,
    page: query.page,
    page_size: PAGE_SIZE,
  });
}

/** A staff member with their linked publications (newest first) for the period. */
export async function loadMember(id, filters, page) {
  const data = await members(`/api/members/${encodeURIComponent(id)}`, {
    ...publicationParams(filters),
    page,
    page_size: PAGE_SIZE,
  });
  return {
    ...data,
    publications: data.rows.map((row) => ({
      id: row.publication_key,
      key: row.publication_key,
      title: row.title,
      year: String(row.year),
      type: row.type,
      oa: capitalise(row.oa_status),
      source: row.sources,
    })),
  };
}
