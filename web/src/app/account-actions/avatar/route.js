import { NextResponse } from 'next/server';
import { apiSend } from '@/lib/api';
import { forbiddenOrigin, sameOrigin, setFlash } from '@/lib/session';

const MAX_BYTES = 2 * 1024 * 1024;

/**
 * Account page: upload (multipart field "photo") or remove ("remove=1") the profile photo.
 * The API checks the real image type from the bytes and the 2 MB limit; the size check here
 * only avoids sending a file that is certain to be refused.
 */
export async function POST(request) {
  if (!sameOrigin(request)) {
    return forbiddenOrigin();
  }
  const form = await request.formData();
  let result;
  if (form.get('remove')) {
    result = await apiSend('DELETE', '/api/auth/me/avatar');
  } else {
    const photo = form.get('photo');
    if (!photo || typeof photo === 'string' || photo.size === 0) {
      result = { ok: false, data: { detail: 'Choose a photo to upload.' } };
    } else if (photo.size > MAX_BYTES) {
      result = { ok: false, data: { detail: 'The photo must be 2 MB or smaller.' } };
    } else {
      result = await apiSend('PUT', '/api/auth/me/avatar', {
        body: Buffer.from(await photo.arrayBuffer()),
        contentType: 'application/octet-stream',
      });
    }
  }
  if (result.status === 401) {
    return NextResponse.redirect(new URL('/login?next=/account', request.url), 303);
  }
  const response = NextResponse.redirect(new URL('/account', request.url), 303);
  const done = form.get('remove') ? 'Your photo is removed.' : 'Your photo is updated.';
  setFlash(response, request, result.ok ? done : (result.data?.detail ?? 'Not saved.'), result.ok ? 'info' : 'error');
  return response;
}
