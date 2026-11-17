import { NextResponse } from 'next/server.js';
import { safeNext } from './session.js';

/** Relative Location keeps the browser on its public origin behind Cloud Run's proxy.
 * request.url can contain the container bind address (0.0.0.0:8080).
 */
export function localRedirect(path, status = 303) {
  return new NextResponse(null, { status, headers: { Location: safeNext(path) } });
}
