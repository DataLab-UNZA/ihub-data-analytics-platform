/**
 * Server-side client for the iHub API (src/ihub/api in the Python project).
 *
 * Call it from server components and route handlers only. The API URL comes from
 * IHUB_API_URL and is never sent to the browser. Requests carry the signed-in user's
 * access token from its httpOnly cookie (ADR-010); a 401 sends the user to sign in.
 */
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { ACCESS_COOKIE } from '@/lib/session';

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

/** The Authorization header for the signed-in user, if there is one. */
async function authHeaders() {
  try {
    const token = (await cookies()).get(ACCESS_COOKIE)?.value;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {}; // outside a request (for example at build time)
  }
}

async function errorFrom(response) {
  let detail = response.statusText;
  try {
    detail = (await response.json()).detail ?? detail;
  } catch {
    /* the body was not JSON */
  }
  return new ApiError(String(detail), response.status);
}

/** Fetches JSON from the API. Throws ApiError when the API is down or answers with an error. */
export async function apiGet(path, params) {
  let response;
  try {
    response = await fetch(buildUrl(path, params), { cache: 'no-store', headers: await authHeaders() });
  } catch (cause) {
    throw new ApiError(`The data service is not reachable at ${API_URL}.`, 503, { cause });
  }
  if (response.status === 401) {
    redirect('/login');
  }
  if (!response.ok) {
    throw await errorFrom(response);
  }
  return response.json();
}

/** Like apiGet, but returns null instead of throwing an ApiError (for optional data). */
export async function apiTry(path, params) {
  try {
    return await apiGet(path, params);
  } catch (error) {
    if (error instanceof ApiError) {
      return null;
    }
    throw error; // lets redirect() through
  }
}

/** Streams a raw API response (used to proxy CSV downloads). */
export async function apiRaw(path, params) {
  return fetch(buildUrl(path, params), { cache: 'no-store', headers: await authHeaders() });
}

/**
 * POSTs JSON to the API without the user's cookie (sign-in routes pass tokens in the body).
 * Returns { ok, status, data }; never throws for HTTP errors.
 */
export async function apiPost(path, body, { token } = {}) {
  try {
    const response = await fetch(buildUrl(path), {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(body ?? {}),
    });
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 503, data: { detail: 'The sign-in service is not reachable. Try again shortly.' } };
  }
}

/** PATCHes JSON as the signed-in user (administration). Returns { ok, status, data }. */
export async function apiPatch(path, body) {
  try {
    const response = await fetch(buildUrl(path), {
      method: 'PATCH',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify(body),
    });
    return { ok: response.ok, status: response.status, data: await response.json().catch(() => null) };
  } catch {
    return { ok: false, status: 503, data: { detail: 'The data service is not reachable.' } };
  }
}

/** The signed-in user (with permissions), or null when signed out or sign-in is off. */
export async function currentUser() {
  const headers = await authHeaders();
  if (!headers.Authorization) {
    return null;
  }
  try {
    const response = await fetch(buildUrl('/api/auth/me'), { cache: 'no-store', headers });
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

/** GETs a public API route (no user token, no redirect). Returns { ok, status, data }. */
export async function apiPublicGet(path) {
  try {
    const response = await fetch(buildUrl(path), { cache: 'no-store' });
    return { ok: response.ok, status: response.status, data: await response.json().catch(() => null) };
  } catch {
    return { ok: false, status: 503, data: { detail: 'The sign-in service is not reachable. Try again shortly.' } };
  }
}

/**
 * Sends a request as the signed-in user (account changes). `json` is sent as JSON; `body`
 * is sent as is with `contentType`. Returns { ok, status, data }; never throws for HTTP errors.
 */
export async function apiSend(method, path, { json, body, contentType } = {}) {
  const headers = { ...(await authHeaders()) };
  if (json !== undefined) headers['Content-Type'] = 'application/json';
  else if (contentType) headers['Content-Type'] = contentType;
  try {
    const response = await fetch(buildUrl(path), {
      method,
      cache: 'no-store',
      headers,
      body: json !== undefined ? JSON.stringify(json) : body,
    });
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } catch {
    return { ok: false, status: 503, data: { detail: 'The service is not reachable. Try again shortly.' } };
  }
}

/**
 * Forwards a request to the API as the signed-in user and returns the raw Response
 * (used by the /bff proxy so browser components can reach the private API).
 */
export async function apiForward(method, path, { search = '', body, contentType } = {}) {
  const headers = { ...(await authHeaders()) };
  if (contentType) headers['Content-Type'] = contentType;
  try {
    return await fetch(`${API_URL}${path}${search}`, { method, cache: 'no-store', headers, body });
  } catch {
    return Response.json({ detail: 'The data service is not reachable.' }, { status: 503 });
  }
}
