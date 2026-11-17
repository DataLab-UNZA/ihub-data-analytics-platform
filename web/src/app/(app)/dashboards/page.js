import { DashboardList } from '@/components/features/workspace/ListViews';
import { apiGet, currentUser } from '@/lib/api';

export const metadata = {
  title: 'Dashboards',
  description: 'Published dashboards, your drafts and your favourites.',
};

export default async function DashboardsPage({ searchParams }) {
  const [{ new: startNew }, dashboards, user] = await Promise.all([searchParams, apiGet('/api/dashboards'), currentUser()]);
  return (
    <DashboardList
      dashboards={dashboards}
      canCreate={user?.permissions?.includes('reports:manage') ?? false}
      startNew={startNew === '1'}
    />
  );
}
