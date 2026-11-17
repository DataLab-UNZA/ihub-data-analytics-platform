import { ChartList } from '@/components/features/workspace/ListViews';
import { apiGet, currentUser } from '@/lib/api';

export const metadata = {
  title: 'Charts',
  description: 'Saved charts built in Explore.',
};

export default async function ChartsPage() {
  const [charts, datasets, user] = await Promise.all([
    apiGet('/api/charts'),
    apiGet('/api/explore/datasets'),
    currentUser(),
  ]);
  return (
    <ChartList charts={charts} datasets={datasets} canCreate={user?.permissions?.includes('reports:manage') ?? false} />
  );
}
