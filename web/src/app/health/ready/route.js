// Cloud Run's frontend intercepts /healthz. Use an application-owned path for deploys.
export const dynamic = 'force-dynamic';
export { GET } from '../../healthz/route';
