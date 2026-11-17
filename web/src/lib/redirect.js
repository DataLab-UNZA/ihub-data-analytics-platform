import { NextResponse } from 'next/server.js';
import { safeNext } from './session.js';

/** Relative Location keeps the browser on its public origin behind Cloud Run's proxy.
 * request.url can contain the container bind address (0.0.0.0:8080).
 */
export function localRedirect(path, status = 303) {
  return new NextResponse(null, { status, headers: { Location: safeNext(path) } });
}

/** Next's proxy adapter requires an absolute Location before normalizing it. */
export function proxyRedirect(path, request, status = 307) {
  const url = new URL(request.url);
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host');
  const protocol = request.headers.get('x-forwarded-proto');
  if (host && /^[a-z0-9.\-\[\]:]+$/i.test(host)) {
    url.port = '';
    url.host = host;
  }
  if (protocol === 'https' || protocol === 'http') url.protocol = `${protocol}:`;
  return NextResponse.redirect(new URL(safeNext(path), url.origin), status);
}
