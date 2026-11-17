/**
 * Sign-in session for the backend-for-frontend (ADR-010).
 *
 * The API issues the tokens; this server keeps them in httpOnly cookies, so browser
 * JavaScript can never read them. Use these helpers from route handlers and the proxy only.
 */

export const ACCESS_COOKIE = 'ihub_at';
export const REFRESH_COOKIE = 'ihub_rt';
export const FLOW_COOKIE = 'ihub_oauth';
export const PENDING_COOKIE = 'ihub_pending';
export const FLASH_COOKIE = 'ihub_flash';
export const DEFAULT_NEXT = '/overview';

/** True unless IHUB_REQUIRE_SIGN_IN is "false" (production sets false until ADR-009 lands). */
export function signInRequired() {
  return process.env.IHUB_REQUIRE_SIGN_IN !== 'false';
}

/** Cookies are Secure whenever the browser reached us over HTTPS (Cloud Run sets the header). */
export function isSecure(request) {
  const proto = request.headers.get('x-forwarded-proto') ?? new URL(request.url).protocol.replace(':', '');
  return proto === 'https';
}

function baseCookie(request, maxAge, path = '/') {
  return { httpOnly: true, sameSite: 'lax', secure: isSecure(request), path, maxAge };
}

/**
 * A same-site path to return to; anything else becomes the overview. Mirrors
 * ihub.auth.service.safe_next_path, so sign-in cannot be used as an open redirect.
 */
export function safeNext(value) {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.includes('\\') ||
    /[\u0000-\u001f\u007f]/.test(value)
  ) {
    return DEFAULT_NEXT;
  }
  return value;
}

/** Store a token pair returned by /api/auth/* on the response. */
export function setTokens(response, request, tokens) {
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, baseCookie(request, tokens.expires_in));
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, baseCookie(request, tokens.refresh_expires_in));
}

/** Remove every sign-in cookie. */
export function clearSession(response) {
  for (const name of [ACCESS_COOKIE, REFRESH_COOKIE, FLOW_COOKIE, PENDING_COOKIE]) {
    response.cookies.delete(name);
  }
}

export function setFlow(response, request, flow, maxAge) {
  response.cookies.set(FLOW_COOKIE, flow, baseCookie(request, maxAge, '/auth/google'));
}

export function setPending(response, request, pending) {
  response.cookies.set(PENDING_COOKIE, JSON.stringify(pending), baseCookie(request, 600));
}

export function readPending(value) {
  try {
    const pending = JSON.parse(value ?? '');
    return typeof pending?.email === 'string' ? { email: pending.email, next: safeNext(pending.next) } : null;
  } catch {
    return null;
  }
}

/**
 * A one-off message for the page this response redirects to (kept out of the URL, so it
 * cannot be spoofed). The cookie is scoped to that page's path, so it never shows elsewhere.
 */
export function setFlash(response, request, message, kind = 'error') {
  const location = response.headers.get('location');
  const path = location ? new URL(location, request.url).pathname : '/';
  response.cookies.set(FLASH_COOKIE, JSON.stringify({ message, kind }), baseCookie(request, 60, path));
}

export function readFlash(value) {
  try {
    const flash = JSON.parse(value ?? '');
    return typeof flash?.message === 'string' ? flash : null;
  } catch {
    return null;
  }
}

/** Seconds until a JWT's `exp`, read without verifying (the API verifies; this only decides when to refresh). */
export function secondsLeft(jwt) {
  try {
    const payload = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const { exp } = JSON.parse(atob(payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), '=')));
    return exp - Date.now() / 1000;
  } catch {
    return -1;
  }
}

/**
 * True when a form POST came from one of our own pages. Browsers send Origin on POST; a
 * different host means another site is submitting the form (cross-site request forgery).
 */
export function sameOrigin(request) {
  const origin = request.headers.get('origin');
  if (!origin) {
    return true; // same-origin navigations from older browsers; SameSite=Lax still applies
  }
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host');
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

/** The response for a refused cross-site POST. */
export function forbiddenOrigin() {
  return new Response('Forbidden: this form must be sent from the iHub site.', { status: 403 });
}

export const EMAIL_CHANGE_COOKIE = 'ihub_email_change';

/** Remember the new address while its confirmation code is on its way (10 minutes). */
export function setEmailChange(response, request, email) {
  response.cookies.set(EMAIL_CHANGE_COOKIE, email, baseCookie(request, 600));
}
