import { NextResponse } from 'next/server';
import { apiSend } from '@/lib/api';
import { forbiddenOrigin, sameOrigin, setEmailChange, setFlash } from '@/lib/session';

/** Account page: send a confirmation code to the new email address. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const form = await request.formData();
  const email = String(form.get('email') ?? '').trim();
  const result = await apiSend('POST', '/api/auth/me/email/request', { json: { email } });
  if (result.status === 401) {
    return NextResponse.redirect(new URL('/login?next=/account', request.url), 303);
  }
  const response = NextResponse.redirect(new URL('/account#email', request.url), 303);
  if (result.ok) {
    setEmailChange(response, request, email);
    setFlash(response, request, `We sent a 6-digit code to ${email}. Enter it to confirm the change.`, 'info');
  } else {
    setFlash(response, request, result.data?.detail ?? 'We could not send a code.');
  }
  return response;
}
