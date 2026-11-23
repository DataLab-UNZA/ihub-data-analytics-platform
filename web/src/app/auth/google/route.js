import { NextResponse } from 'next/server';
import { localRedirect } from '@/lib/redirect';
import { apiPost } from '@/lib/api';
import { safeNext, setFlash, setFlow } from '@/lib/session';

/**
 * Step 1 of Google sign-in: ask the API for Google's authorisation URL (with PKCE, state
 * and nonce), keep the signed flow state in an httpOnly cookie, and send the browser to Google.
 */
export async function GET(request) {
  const next = safeNext(new URL(request.url).searchParams.get('next'));
  const result = await apiPost('/api/auth/google/start', { next });
  if (!result.ok) {
    const response = localRedirect('/login');
    setFlash(response, request, result.data?.detail ?? 'Sign-in with Google is not available.');
    return response;
  }
  const response = NextResponse.redirect(result.data.authorization_url, 303);
  setFlow(response, request, result.data.flow, result.data.flow_expires_in);
  return response;
}
