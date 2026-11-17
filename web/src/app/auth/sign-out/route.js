import { NextResponse } from 'next/server';
import { apiPost } from '@/lib/api';
import { REFRESH_COOKIE, clearSession, setFlash, forbiddenOrigin, sameOrigin } from '@/lib/session';

/** Sign out (form POST): revoke the session in the API, then clear every sign-in cookie. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (refreshToken) {
    await apiPost('/api/auth/sign-out', { refresh_token: refreshToken });
  }
  const response = NextResponse.redirect(new URL('/login', request.url), 303);
  clearSession(response);
  setFlash(response, request, 'You are signed out.', 'info');
  return response;
}
