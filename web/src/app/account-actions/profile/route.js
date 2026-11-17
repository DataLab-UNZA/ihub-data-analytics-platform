import { NextResponse } from 'next/server';
import { apiSend } from '@/lib/api';
import { forbiddenOrigin, sameOrigin, setFlash } from '@/lib/session';

/** Account page: save the name and phone. */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const form = await request.formData();
  const result = await apiSend('PATCH', '/api/auth/me', {
    json: { name: String(form.get('name') ?? ''), phone: String(form.get('phone') ?? '') },
  });
  if (result.status === 401) {
    return NextResponse.redirect(new URL('/login?next=/account', request.url), 303);
  }
  const response = NextResponse.redirect(new URL('/account', request.url), 303);
  setFlash(response, request, result.ok ? 'Your details are saved.' : (result.data?.detail ?? 'Not saved.'), result.ok ? 'info' : 'error');
  return response;
}
