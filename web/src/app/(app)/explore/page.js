import ExploreView from '@/components/features/explore/ExploreView';
import { apiGet, apiTry, currentUser } from '@/lib/api';

export const metadata = {
  title: 'Explore',
  description: 'Build a chart from the research data: choose a dataset, metrics, group-by columns and filters.',
};

/** Explore (Apache Superset's chart builder): a new chart, or ?chart=<id> to edit a saved one. */
export default async function ExplorePage({ searchParams }) {
  const { chart: chartId } = await searchParams;
  const [datasets, user, dashboards, chart] = await Promise.all([
    apiGet('/api/explore/datasets'),
    currentUser(),
    apiTry('/api/dashboards'),
    chartId ? apiTry(`/api/charts/${encodeURIComponent(chartId)}`) : null,
  ]);
  return (
    <ExploreView
      key={chart?.chart_id ?? 'new'}
      datasets={datasets}
      chart={chart}
      user={user}
      dashboards={dashboards ?? []}
    />
  );
}
