import PageHeader from '@/components/layout/PageHeader';
import InstitutionDashboard from '@/components/features/dashboard/InstitutionDashboard';
import { DashboardList } from '@/components/features/workspace/ListViews';
import Alert from '@/components/ui/Alert';
import { apiGet, currentUser, optional } from '@/lib/api';
import { readFilters } from '@/lib/filters-server';
import { loadDashboard } from '@/services/dashboard';

export const metadata = {
  title: 'Dashboards',
  description: 'The university at a glance: research, student information and HR, and your saved dashboards.',
};

/**
 * Dashboards: the institutional dashboard (research and IRIMS live; student records, Moodle and
 * HR as sample data until connected), then the saved dashboards of a signed-in user. When the
 * research data or the saved dashboards cannot be loaded, the other part still shows, with a notice.
 */
export default async function DashboardsPage({ searchParams }) {
  const user = await currentUser();
  const [{ new: startNew }, data, dashboards] = await Promise.all([
    searchParams,
    optional(loadDashboard(await readFilters())),
    // Saved dashboards belong to a signed-in user; when their store fails, the rest still shows.
    user ? optional(apiGet('/api/dashboards')) : null,
  ]);
  return (
    <>
      <PageHeader title="The university at a glance" />
      {data ? (
        <InstitutionDashboard data={data} />
      ) : (
        <Alert id="dashboard-unavailable" variant="banner" role="status" title="The university dashboard is unavailable">
          The research data service did not answer, so the charts cannot be drawn. Try again shortly, or check the data
          sources.
        </Alert>
      )}
      {user && (
        <section className="dash-saved" aria-label="Saved dashboards">
          {dashboards ? (
            <DashboardList
              dashboards={dashboards}
              canCreate={user.permissions?.includes('reports:manage') ?? false}
              startNew={startNew === '1'}
              heading="Saved dashboards"
              as="h2"
            />
          ) : (
            <Alert id="saved-dashboards-unavailable" variant="banner" role="status" title="Saved dashboards are unavailable">
              The store that keeps saved dashboards did not answer. The dashboard above is not affected.
            </Alert>
          )}
        </section>
      )}
    </>
  );
}
