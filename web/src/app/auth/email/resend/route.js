import { localRedirect } from '@/lib/redirect';
import { apiPost } from '@/lib/api';
import { PENDING_COOKIE, readPending, setFlash, forbiddenOrigin, sameOrigin } from '@/lib/session';

/** Email sign-in: send a fresh code to the address waiting on the code screen. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const pending = readPending(request.cookies.get(PENDING_COOKIE)?.value);
  const target = pending ? '/verify-code' : '/login';
  const response = localRedirect(target);
  if (!pending) {
    setFlash(response, request, 'Enter your email address to get a code.');
    return response;
  }
  const result = await apiPost('/api/auth/email/request', { email: pending.email });
  setFlash(
    response,
    request,
    result.ok ? 'We sent a new code. Use the newest email.' : (result.data?.detail ?? 'We could not send a code.'),
    result.ok ? 'info' : 'error',
  );
  return response;
}
