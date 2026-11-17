import { localRedirect } from '@/lib/redirect';
import { apiPost } from '@/lib/api';
import { FLOW_COOKIE, safeNext, setFlash, setTokens } from '@/lib/session';

/**
 * Step 2 of Google sign-in: Google sends the browser back here with a code and the state.
 * The API checks the state against the signed flow, exchanges the code with Google and
 * verifies the ID token; we store the tokens it issues and continue to the page asked for.
 */
export async function GET(request) {
  const params = new URL(request.url).searchParams;
  const flow = request.cookies.get(FLOW_COOKIE)?.value;
  const fail = (message) => {
    const response = localRedirect('/login');
    response.cookies.delete({ name: FLOW_COOKIE, path: '/auth/google' });
    setFlash(response, request, message);
    return response;
  };

  if (params.get('error')) {
    return fail('Google sign-in was cancelled.');
  }
  const code = params.get('code');
  const state = params.get('state');
  if (!code || !state || !flow) {
    return fail('This sign-in attempt has expired. Start again.');
  }

  const result = await apiPost('/api/auth/google/callback', { code, state, flow });
  if (!result.ok) {
    return fail(result.data?.detail ?? 'Google sign-in failed. Start again.');
  }
  const response = localRedirect(safeNext(result.data.next));
  response.cookies.delete({ name: FLOW_COOKIE, path: '/auth/google' });
  setTokens(response, request, result.data);
  return response;
}
