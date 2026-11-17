import { NextResponse } from 'next/server';
import { apiPost } from '@/lib/api';
import { safeNext, setFlash, setPending, forbiddenOrigin, sameOrigin } from '@/lib/session';

/**
 * Email sign-in, step 1 (form POST from /login): ask the API to email a one-time code.
 * The address and return path wait in an httpOnly cookie for the code screen.
 */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const form = await request.formData();
  const email = String(form.get('email') ?? '').trim();
  const next = safeNext(String(form.get('next') ?? ''));

  const result = await apiPost('/api/auth/email/request', { email });
  if (!result.ok) {
    const response = NextResponse.redirect(new URL('/login', request.url), 303);
    setFlash(response, request, result.data?.detail ?? 'We could not send a code. Try again.');
    return response;
  }
  const response = NextResponse.redirect(new URL('/verify-code', request.url), 303);
  setPending(response, request, { email, next });
  setFlash(response, request, 'We sent a 6-digit code. It expires in 10 minutes.', 'info');
  return response;
}
