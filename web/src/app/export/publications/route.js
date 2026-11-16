import { apiRaw } from '@/lib/api';

/**
 * Proxies the CSV export so the browser never needs the data service's address.
 * The query string carries the filters (see services/publications.js buildQuery).
 */
export async function GET(request) {
  const params = {};
  for (const [key, value] of new URL(request.url).searchParams) {
    params[key] = params[key] ? [].concat(params[key], value) : value;
  }

  let upstream;
  try {
    upstream = await apiRaw('/api/publications/export', params);
  } catch {
    return new Response('The data service is not reachable.', { status: 503 });
  }
  if (!upstream.ok) {
    return new Response('The export could not be created.', { status: upstream.status });
  }
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="ihub-publications.csv"',
    },
  });
}
