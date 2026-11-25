import PageHeader from '@/components/layout/PageHeader';
import FeaturedCharts, { ExploreCallout } from '@/components/features/charts/FeaturedCharts';
import { ChartList } from '@/components/features/workspace/ListViews';
import Alert from '@/components/ui/Alert';
import { apiGet, currentUser, optional } from '@/lib/api';
import { loadFeatured } from '@/services/explore';

export const metadata = {
  title: 'Charts',
  description: 'The most used charts for each module, your saved charts, and a way into Explore.',
};

/**
 * Charts: the most used ready-made charts, grouped by module (research is live; HR, student
 * information and learning management show sample data until they are connected), then the
 * saved charts, then a way into Explore for everything else.
 */
export default async function ChartsPage() {
  const user = await currentUser();
  // Saved charts belong to a signed-in user; a visitor (sign-in turned off) sees the rest, and
  // when the saved-charts store fails the main charts still show.
  const [modules, charts, datasets] = await Promise.all([
    loadFeatured(user),
    user ? optional(apiGet('/api/charts')) : null,
    user ? optional(apiGet('/api/explore/datasets')) : null,
  ]);
  return (
    <>
      <PageHeader title="Charts" filters={false} />
      <p className="guide-intro">The charts people look at most, for each module. Open any chart in Explore to filter it and see the numbers.</p>
      <FeaturedCharts modules={modules} />
      {user && (
        <section className="charts-saved" aria-label="Saved charts">
          {charts && datasets ? (
            <ChartList charts={charts} datasets={datasets} canCreate={user.permissions?.includes('reports:manage') ?? false} title="Saved charts" as="h2" />
          ) : (
            <Alert id="saved-charts-unavailable" variant="banner" role="status" title="Saved charts are unavailable">
              The store that keeps saved charts did not answer. The charts above are not affected.
            </Alert>
          )}
        </section>
      )}
      <ExploreCallout />
    </>
  );
}
