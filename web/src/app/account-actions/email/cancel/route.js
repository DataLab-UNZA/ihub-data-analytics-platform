import { NextResponse } from 'next/server';
import { EMAIL_CHANGE_COOKIE, forbiddenOrigin, sameOrigin } from '@/lib/session';

/** Account page: forget a pending email change. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const response = NextResponse.redirect(new URL('/account#email', request.url), 303);
  response.cookies.delete(EMAIL_CHANGE_COOKIE);
  return response;
}
