import OverviewDashboard from '@/components/features/overview/OverviewDashboard';
import { readFilters } from '@/lib/filters-server';
import { loadOverview } from '@/services/overview';

export const metadata = {
  title: 'Overview (stale data)',
  description: 'Overview showing the last trusted snapshot because the weekly source refresh is overdue.',
};

/** Design preview of the stale state: always shows the banner over the real data. */
export default async function StaleOverviewPage() {
  const data = await loadOverview(await readFilters());
  return <OverviewDashboard data={data} showStale />;
}
