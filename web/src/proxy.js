import { NextResponse } from 'next/server';
import {
  ACCESS_COOKIE,
  DEFAULT_NEXT,
  REFRESH_COOKIE,
  clearSession,
  secondsLeft,
  setTokens,
  signInRequired,
} from '@/lib/session';

/**
 * Runs before every page (ADR-010):
 *
 * 1. Signed-out visitors are sent to /login, which brings them back afterwards.
 * 2. When the access token has expired (15 minutes) but the refresh token is valid, the
 *    proxy refreshes both silently. The new cookies reach the page in the same request.
 * 3. Signed-in visitors skip /login and /verify-code.
 * 4. The developer screen index at "/" opens the overview in production.
 *
 * With IHUB_REQUIRE_SIGN_IN=false (production until ADR-009's store exists) pages stay
 * open and the sign-in screens send visitors to the overview.
 */
const SIGN_IN_PAGES = ['/login', '/verify-code'];
const PUBLIC_PREFIXES = ['/auth/', '/healthz', '/foundations'];
const API_URL = (process.env.IHUB_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
const REFRESH_MARGIN_SECONDS = 30;

function isSignInPage(pathname) {
  return SIGN_IN_PAGES.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

function showScreenIndex() {
  const flag = process.env.IHUB_SHOW_PREVIEWS;
  return flag === undefined ? process.env.NODE_ENV !== 'production' : flag === 'true';
}

async function refreshTokens(refreshToken) {
  try {
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: 'no-store',
    });
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

function toLogin(request) {
  const url = new URL('/login', request.url);
  const { pathname, search } = request.nextUrl;
  if (pathname !== '/' && pathname !== DEFAULT_NEXT) {
    url.searchParams.set('next', `${pathname}${search}`);
  }
  return NextResponse.redirect(url);
}

export async function proxy(request) {
  const { pathname } = request.nextUrl;

  if (pathname === '/' && !showScreenIndex()) {
    return NextResponse.redirect(new URL(DEFAULT_NEXT, request.url));
  }
  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }
  if (!signInRequired()) {
    // A code may have been requested just before the setting changed or on a revision
    // that has not restarted yet. Let the code screen read its pending cookie; without
    // one it redirects safely through /login to the public overview.
    return pathname === '/login' ? NextResponse.redirect(new URL(DEFAULT_NEXT, request.url)) : NextResponse.next();
  }

  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  const accessValid = Boolean(access) && secondsLeft(access) > REFRESH_MARGIN_SECONDS;

  if (accessValid) {
    return isSignInPage(pathname) ? NextResponse.redirect(new URL(DEFAULT_NEXT, request.url)) : NextResponse.next();
  }
  if (refresh) {
    const tokens = await refreshTokens(refresh);
    if (tokens) {
      const response = isSignInPage(pathname)
        ? NextResponse.redirect(new URL(DEFAULT_NEXT, request.url))
        : NextResponse.next();
      setTokens(response, request, tokens);
      return response;
    }
  }
  if (isSignInPage(pathname)) {
    return NextResponse.next();
  }
  const response = toLogin(request);
  if (access || refresh) {
    clearSession(response); // expired or revoked: start clean
  }
  return response;
}

export const config = {
  // Every page and route except Next.js assets and static files.
  matcher: ['/((?!_next/static|_next/image|img/|favicon.ico).*)'],
};
