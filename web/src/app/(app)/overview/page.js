import OverviewDashboard from '@/components/features/overview/OverviewDashboard';
import { readFilters } from '@/lib/filters-server';
import { loadOverview } from '@/services/overview';

export const metadata = {
  title: 'Overview',
  description: 'Executive overview of University of Zambia research output, open access, citations and collaboration.',
};

/** Reads the global filters from the cookie and shows the real overview. A failure reaches error.js. */
export default async function OverviewPage() {
  const data = await loadOverview(await readFilters());
  return <OverviewDashboard data={data} showStale={data.stale.isStale} />;
}
