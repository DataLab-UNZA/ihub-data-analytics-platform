import { apiRaw } from '@/lib/api';

/**
 * The signed-in user's profile photo, streamed from the API with their token, so an
 * <img src="/me/avatar"> works without the browser ever holding a token.
 */
export async function GET() {
  const upstream = await apiRaw('/api/auth/me/avatar');
  if (!upstream.ok) {
    return new Response(null, { status: upstream.status === 401 ? 401 : 404 });
  }
  return new Response(upstream.body, {
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/octet-stream',
      'Cache-Control': 'private, max-age=300',
      'X-Content-Type-Options': 'nosniff',
    },
  });
}
