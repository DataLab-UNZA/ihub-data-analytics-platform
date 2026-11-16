import Link from 'next/link';
import OrganisationExplorer from '@/components/features/organisation/OrganisationExplorer';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import { readFilters } from '@/lib/filters-server';
import { loadOrganisation } from '@/services/research';

export const metadata = {
  title: 'Organisation',
  description: 'Browse University of Zambia units and departments with their publication totals.',
};

export default async function OrganisationPage() {
  const { tree, schoolCount, unitCount } = await loadOrganisation(await readFilters());

  return (
    <>
      <PageHeader title="Organisation" />
      <OrganisationExplorer
        tree={tree}
        subtitle={
          <>
            {schoolCount} units · {unitCount} departments and centres · labels can be renamed in{' '}
            <Link href="/admin/hierarchy">Admin</Link>
          </>
        }
      >
        <Card aria-labelledby="structure-title">
          <CardHeader id="structure-title" title="How units are counted" className="mb-32" />
          <h3>Organisation &gt; Unit &gt; Department</h3>
          <p className="text-muted mt-24">
            A publication counts once in every school with an author, so unit totals add up to more than the
            university total. Publications that cannot be mapped to a department appear under “Unassigned department”.
          </p>
          <h3 className="subhead--plain mt-40 text-md">Your access</h3>
          <p className="mt-8">
            <Link href="/admin/users">Executive · all units</Link>
          </p>
          <p className="text-muted mt-24">Unit heads see only their own unit and sub-units.</p>
        </Card>
      </OrganisationExplorer>
    </>
  );
}
