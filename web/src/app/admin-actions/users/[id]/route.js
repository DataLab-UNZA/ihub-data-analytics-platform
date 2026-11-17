import { NextResponse } from 'next/server';
import { apiPatch } from '@/lib/api';
import { forbiddenOrigin, sameOrigin, setFlash } from '@/lib/session';

const ROLES = new Set(['member', 'analyst', 'librarian', 'unit-head', 'executive', 'admin']);
const STATUSES = new Set(['active', 'deactivated']);

/**
 * Users & roles form POST: change one user's role or status through the API, which checks
 * the caller's users:manage permission and refuses changes to the caller's own access.
 */
export async function POST(request, { params }) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const { id } = await params;
  const form = await request.formData();
  const body = {};
  const role = String(form.get('role') ?? '');
  const status = String(form.get('status') ?? '');
  if (ROLES.has(role)) body.role = role;
  if (STATUSES.has(status)) body.status = status;

  const response = NextResponse.redirect(new URL('/admin/users', request.url), 303);
  const result = await apiPatch(`/api/admin/users/${encodeURIComponent(id)}`, body);
  if (result.status === 401) {
    return NextResponse.redirect(new URL('/login', request.url), 303);
  }
  setFlash(
    response,
    request,
    result.ok ? `Saved: ${result.data.email} is now ${result.data.role} (${result.data.status}).` : (result.data?.detail ?? 'The change was not saved.'),
    result.ok ? 'info' : 'error',
  );
  return response;
}
