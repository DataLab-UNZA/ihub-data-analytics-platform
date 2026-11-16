import { FILTER_COOKIE } from '@/config/filters';

/**
 * Persisted global filters, kept in a cookie so server components can apply them
 * and exposed as an external store so React can read them with useSyncExternalStore.
 */
const EMPTY = Object.freeze({});
const MAX_AGE_SECONDS = 60 * 60 * 24 * 365;
const listeners = new Set();
let cache = { raw: null, parsed: EMPTY };

/** Parses a cookie value (used on the server and in the browser). */
export function parseFilters(raw) {
  if (!raw) {
    return EMPTY;
  }
  try {
    const value = JSON.parse(decodeURIComponent(raw));
    return value && typeof value === 'object' && !Array.isArray(value) ? value : EMPTY;
  } catch {
    return EMPTY;
  }
}

function readRaw() {
  const entry = document.cookie.split('; ').find((part) => part.startsWith(`${FILTER_COOKIE}=`));
  return entry ? entry.slice(FILTER_COOKIE.length + 1) : null;
}

export function getSnapshot() {
  const raw = readRaw();
  if (raw === cache.raw) {
    return cache.parsed;
  }
  cache = { raw, parsed: parseFilters(raw) };
  return cache.parsed;
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function saveFilters(value) {
  const encoded = encodeURIComponent(JSON.stringify(value));
  document.cookie = `${FILTER_COOKIE}=${encoded}; path=/; max-age=${MAX_AGE_SECONDS}; samesite=lax`;
  listeners.forEach((listener) => listener());
}
