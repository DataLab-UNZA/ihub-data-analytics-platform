import { apiForward } from '@/lib/api';
import { forbiddenOrigin, sameOrigin } from '@/lib/session';

/**
 * Backend-for-frontend proxy for interactive screens (Explore, charts, dashboards).
 * Browser components call /bff/<path>; this forwards to /api/<path> with the user's token
 * from its httpOnly cookie. Only these API areas are reachable, and writes must come from
 * our own pages (Origin check). The API applies RBAC to every call.
 */
const ALLOWED = new Set(['explore', 'charts', 'dashboards']);

async function forward(request, { params }) {
  const { path } = await params;
  if (!path?.length || !ALLOWED.has(path[0])) {
    return Response.json({ detail: 'Not found.' }, { status: 404 });
  }
  if (request.method !== 'GET' && !sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const target = `/api/${path.map(encodeURIComponent).join('/')}`;
  const body = ['GET', 'HEAD'].includes(request.method) ? undefined : await request.text();
  const upstream = await apiForward(request.method, target, {
    search: new URL(request.url).search,
    body,
    contentType: body ? (request.headers.get('content-type') ?? 'application/json') : undefined,
  });
  const headers = new Headers({ 'Cache-Control': 'no-store' });
  for (const name of ['content-type', 'content-disposition']) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new Response(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers });
}

export { forward as DELETE, forward as GET, forward as PATCH, forward as POST, forward as PUT };
