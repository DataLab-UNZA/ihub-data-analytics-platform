import { NextResponse } from 'next/server';
import { apiPost } from '@/lib/api';
import { PENDING_COOKIE, readPending, setFlash, setTokens, forbiddenOrigin, sameOrigin } from '@/lib/session';

/** Email sign-in, step 2 (form POST from /verify-code): check the code and sign in. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const pending = readPending(request.cookies.get(PENDING_COOKIE)?.value);
  if (!pending) {
    const response = NextResponse.redirect(new URL('/login', request.url), 303);
    setFlash(response, request, 'Your sign-in attempt expired. Ask for a new code.');
    return response;
  }
  const form = await request.formData();
  const code =
    String(form.get('code') ?? '') ||
    Array.from({ length: 6 }, (_, i) => String(form.get(`code-${i + 1}`) ?? '')).join('');

  const result = await apiPost('/api/auth/email/verify', { email: pending.email, code });
  if (!result.ok) {
    const response = NextResponse.redirect(new URL('/verify-code', request.url), 303);
    setFlash(response, request, result.data?.detail ?? 'That code did not work.');
    return response;
  }
  const response = NextResponse.redirect(new URL(pending.next, request.url), 303);
  response.cookies.delete(PENDING_COOKIE);
  setTokens(response, request, result.data);
  return response;
}
