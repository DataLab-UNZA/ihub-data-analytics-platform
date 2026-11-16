import { apiTry } from '@/lib/api';

const CAT_OFFSET_HOURS = 2; // Lusaka time (Central Africa Time), no daylight saving
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Formats an ISO timestamp (UTC) as "16 Nov 2026 · 06:00 CAT". Returns null for no value. */
export function formatRefreshed(iso) {
  if (!iso) {
    return null;
  }
  const date = new Date(new Date(iso.endsWith('Z') ? iso : `${iso}Z`).getTime() + CAT_OFFSET_HOURS * 3600_000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()} · ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())} CAT`;
}

/** True when the pipeline has not run for more than `days` days. Unknown counts as not stale. */
export function isStale(iso, days = 8) {
  if (!iso) {
    return false;
  }
  const last = new Date(iso.endsWith('Z') ? iso : `${iso}Z`).getTime();
  return Date.now() - last > days * 86_400_000;
}

/**
 * Data the shell needs on every signed-in screen: the real filter options and the
 * time of the last pipeline run. Returns nulls when the data service is down, so the
 * shell still renders with its static fallbacks.
 */
export async function loadShellData() {
  const [filters, health] = await Promise.all([apiTry('/api/filters'), apiTry('/api/health')]);

  const options = filters
    ? {
        period: [
          ['all', 'All years'],
          ...Array.from({ length: filters.years.end - filters.years.start + 1 }, (_, i) => {
            const year = String(filters.years.end - i);
            return [year, year];
          }),
        ],
        unit: [['organisation', 'Organisation'], ...filters.schools.map((school) => [school, school])],
        type: [['all', 'All outputs'], ...filters.types.map((type) => [type, type])],
      }
    : undefined;

  return { options, lastRun: health?.last_pipeline_run ?? null, online: Boolean(health) };
}
