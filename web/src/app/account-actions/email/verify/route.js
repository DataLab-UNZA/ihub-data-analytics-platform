import { NextResponse } from 'next/server';
import { apiSend } from '@/lib/api';
import { EMAIL_CHANGE_COOKIE, forbiddenOrigin, sameOrigin, setFlash } from '@/lib/session';

/** Account page: confirm the new email address with the code sent to it. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const email = request.cookies.get(EMAIL_CHANGE_COOKIE)?.value;
  const response = NextResponse.redirect(new URL('/account#email', request.url), 303);
  if (!email) {
    setFlash(response, request, 'The change expired. Enter the new address again.');
    return response;
  }
  const form = await request.formData();
  const code =
    String(form.get('code') ?? '') ||
    Array.from({ length: 6 }, (_, i) => String(form.get(`code-${i + 1}`) ?? '')).join('');
  const result = await apiSend('POST', '/api/auth/me/email/verify', { json: { email, code } });
  if (result.status === 401) {
    return NextResponse.redirect(new URL('/login?next=/account', request.url), 303);
  }
  if (result.ok) {
    response.cookies.delete(EMAIL_CHANGE_COOKIE);
    setFlash(response, request, `Your email is now ${result.data.email}.`, 'info');
  } else {
    setFlash(response, request, result.data?.detail ?? 'That code did not work.');
  }
  return response;
}
