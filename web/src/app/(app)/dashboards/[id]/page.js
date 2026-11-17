import { notFound } from 'next/navigation';
import DashboardView from '@/components/features/workspace/DashboardView';
import { apiGet, apiTry, currentUser } from '@/lib/api';

export const metadata = {
  title: 'Dashboard',
  description: 'Charts and filters on one page.',
};

/** One dashboard; ?edit=1 opens it in edit mode for its owner or an administrator. */
export default async function DashboardPage({ params, searchParams }) {
  const [{ id }, { edit }] = await Promise.all([params, searchParams]);
  const [dashboard, charts, datasets, user] = await Promise.all([
    apiTry(`/api/dashboards/${encodeURIComponent(id)}`),
    apiGet('/api/charts'),
    apiGet('/api/explore/datasets'),
    currentUser(),
  ]);
  if (!dashboard) {
    notFound();
  }
  return (
    <DashboardView
      key={dashboard.dashboard_id}
      dashboard={dashboard}
      charts={charts}
      datasets={datasets}
      user={user}
      startEditing={edit === '1'}
    />
  );
}
