import { ApiError, apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';

/**
 * Health check for the deploy workflow: 200 when the front end is up and the research API
 * sidecar answers, 503 otherwise. Reports whether the mart is readable, never any data.
 */
export async function GET() {
  try {
    const api = await apiGet('/api/health');
    return Response.json({
      status: 'ok',
      api: 'ok',
      mart_available: Boolean(api.mart_available),
      last_pipeline_run: api.last_pipeline_run ?? null,
    });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 503;
    return Response.json({ status: 'degraded', api: 'unreachable', detail: `API answered ${status}` }, { status: 503 });
  }
}
