import { notFound, redirect } from 'next/navigation';
import PageHeader from '@/components/layout/PageHeader';
import GuideView from '@/components/features/explore/GuideView';
import { apiTry, currentUser } from '@/lib/api';
import { filtersFromParams } from '@/lib/guides';
import { can } from '@/lib/permissions';
import { loadCatalogue, loadFilterOptions } from '@/services/explore';

export const metadata = {
  title: 'Ready-made chart',
  description: 'A ready-made chart that answers a plain question about UNZA research.',
};

export default async function GuidePage({ params, searchParams }) {
  const { id } = await params;
  const user = await currentUser();
  const [themes, options, dashboards] = await Promise.all([loadCatalogue(user), loadFilterOptions(), user ? apiTry('/api/dashboards') : null]);
  const theme = themes.find((item) => item.guides.some((guide) => guide.id === id));
  if (!theme) {
    // A chart that exists but is not for this visitor (data quality) is a 403, anything else a 404.
    const all = await loadCatalogue(null);
    if (all.some((item) => item.guides.some((guide) => guide.id === id))) redirect('/access-restricted');
    notFound();
  }
  const guide = theme.guides.find((item) => item.id === id);
  return (
    <>
      <PageHeader title="Explore" filters={false} />
      <GuideView
        key={guide.id}
        guide={guide}
        theme={theme}
        options={options}
        initial={filtersFromParams(await searchParams)}
        canSave={can(user, 'reports:manage')}
        canExport={can(user, 'research:export')}
        canBuild={can(user, 'research:read')}
        dashboards={dashboards ?? []}
      />
    </>
  );
}
