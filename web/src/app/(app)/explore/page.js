import PageHeader from '@/components/layout/PageHeader';
import ExploreHome from '@/components/features/explore/ExploreHome';
import ExploreView from '@/components/features/explore/ExploreView';
import { apiGet, apiTry, currentUser } from '@/lib/api';
import { can } from '@/lib/permissions';
import { loadCatalogue } from '@/services/explore';

export const metadata = {
  title: 'Explore',
  description: 'Ready-made charts that answer common questions about UNZA research, and a chart builder.',
};

/**
 * Explore. With no chart in the address it is the gallery of ready-made charts; with
 * ?chart=<id> it opens that saved chart in the chart builder (for editing).
 */
export default async function ExplorePage({ searchParams }) {
  const { chart: chartId } = await searchParams;
  if (chartId) {
    const [datasets, user, dashboards, chart] = await Promise.all([
      apiGet('/api/explore/datasets'),
      currentUser(),
      apiTry('/api/dashboards'),
      apiTry(`/api/charts/${encodeURIComponent(chartId)}`),
    ]);
    return <ExploreView key={chart?.chart_id ?? 'new'} datasets={datasets} chart={chart} user={user} dashboards={dashboards ?? []} />;
  }

  const user = await currentUser();
  const themes = await loadCatalogue(user);
  return (
    <>
      <PageHeader title="Explore" filters={false} />
      <p className="guide-intro">
        Pick a question to see the answer as a chart. Every chart can be narrowed by year, kind of publication or school, and
        explained in plain words.
      </p>
      <ExploreHome themes={themes} canBuild={can(user, 'research:read')} />
    </>
  );
}
