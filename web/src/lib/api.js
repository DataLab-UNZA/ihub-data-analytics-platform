/**
 * Server-side client for the iHub research API (src/ihub/api in the Python project).
 *
 * Call it from server components and route handlers only. The API URL comes from
 * IHUB_API_URL and is never sent to the browser.
 */
const API_URL = (process.env.IHUB_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function buildUrl(path, params = {}) {
  const url = new URL(`${API_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined && item !== null && item !== '') {
        url.searchParams.append(key, String(item));
      }
    }
  }
  return url;
}

/** Fetches JSON from the API. Throws ApiError when the API is down or answers with an error. */
export async function apiGet(path, params) {
  let response;
  try {
    response = await fetch(buildUrl(path, params), { cache: 'no-store' });
  } catch (cause) {
    throw new ApiError(`The data service is not reachable at ${API_URL}.`, 503, { cause });
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* the body was not JSON */
    }
    throw new ApiError(String(detail), response.status);
  }
  return response.json();
}

/** Like apiGet, but returns null instead of throwing (for optional, non-essential data). */
export async function apiTry(path, params) {
  try {
    return await apiGet(path, params);
  } catch {
    return null;
  }
}

/** Streams a raw API response (used to proxy CSV downloads). */
export async function apiRaw(path, params) {
  return fetch(buildUrl(path, params), { cache: 'no-store' });
}
