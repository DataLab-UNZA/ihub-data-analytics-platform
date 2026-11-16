import { cookies } from 'next/headers';
import { FILTER_COOKIE, FILTER_DEFAULTS, SOURCE_NAMES } from '@/config/filters';
import { parseFilters } from '@/lib/filter-store';

/** Reads the global filters the browser saved in its cookie (server components only). */
export async function readFilters() {
  const jar = await cookies();
  return { ...FILTER_DEFAULTS, ...parseFilters(jar.get(FILTER_COOKIE)?.value) };
}

/** API query parameters for the period filter ("all" leaves both ends open). */
export function yearParams(filters) {
  return /^\d{4}$/.test(filters.period) ? { start: filters.period, end: filters.period } : {};
}

/** API query parameters for the publication list: period, source and type. */
export function publicationParams(filters) {
  const params = { ...yearParams(filters) };
  if (SOURCE_NAMES[filters.source]) {
    params.source = SOURCE_NAMES[filters.source];
  }
  if (filters.type && filters.type !== 'all') {
    params.type = filters.type;
  }
  return params;
}

/** Human label for the active period, e.g. "1961 to 2027" or "2024". */
export function periodLabel(years) {
  return years.start === years.end ? String(years.start) : `${years.start} to ${years.end}`;
}
