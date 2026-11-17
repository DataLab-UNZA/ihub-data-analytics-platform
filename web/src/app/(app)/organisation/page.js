import Link from 'next/link';
import OrganisationExplorer from '@/components/features/organisation/OrganisationExplorer';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import BarList from '@/components/ui/BarList';
import DataTable from '@/components/ui/DataTable';
import { readFilters } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadOrganisation } from '@/services/research';

export const metadata = {
  title: 'Organisation',
  description: 'University of Zambia schools and units with the publications credited to each.',
};

const COLUMNS = [
  { key: 'school', header: 'School or unit', rowHeader: true },
  { key: 'roster', header: 'Publications (staff roster)' },
  { key: 'any', header: 'Incl. department evidence' },
  { key: 'authors', header: 'Authors matched' },
  { key: 'staff', header: 'Staff matched' },
];

/** Explains how the numbers were made, in numbers only (never names). */
function CreditMethod({ credit }) {
  const { coverage, stats } = credit;
  return (
    <Card aria-labelledby="structure-title">
      <CardHeader id="structure-title" title="How schools are credited" className="mb-32" />
      <h3>Authors matched to the staff roster</h3>
      <p className="text-muted mt-24">
        Each UNZA author is matched by name to the staff roster, and the publication is credited to that person&rsquo;s
        school. A publication counts once in every school with a matched author, so school totals add up to more than
        the university total.
      </p>
      <h3 className="subhead--plain mt-40 text-md">Coverage</h3>
      <p className="text-muted mt-8">
        {formatNumber(coverage.byRoster)} of {formatNumber(coverage.total)} publications ({coverage.share}) have an
        author linked through the roster. {formatNumber(stats.linked)} of {formatNumber(stats.authors)} UNZA authors
        and {formatNumber(stats.staffMatched)} of {formatNumber(stats.headcount)} staff on the roster were matched.
      </p>
      <p className="text-muted mt-16">
        Names fitting more than one person are left out ({formatNumber(stats.ambiguous)}). Authors not on the roster
        keep their department-based school, shown separately.
      </p>
    </Card>
  );
}

/** Explains the fallback when no roster is loaded. */
function DepartmentMethod() {
  return (
    <Card aria-labelledby="structure-title">
      <CardHeader id="structure-title" title="How units are counted" className="mb-32" />
      <h3>Organisation &gt; Unit &gt; Department</h3>
      <p className="text-muted mt-24">
        A publication counts once in every school with an author, so unit totals add up to more than the university
        total. Publications that cannot be mapped to a department appear under &ldquo;Unassigned department&rdquo;.
      </p>
      <h3 className="subhead--plain mt-40 text-md">Your access</h3>
      <p className="mt-8">
        <Link href="/admin/users">Executive · all units</Link>
      </p>
      <p className="text-muted mt-24">Unit heads see only their own unit and sub-units.</p>
    </Card>
  );
}

export default async function OrganisationPage() {
  const { tree, credit, schoolCount, unitCount } = await loadOrganisation(await readFilters());

  return (
    <>
      <PageHeader title="Organisation" />
      <OrganisationExplorer
        tree={tree}
        subtitle={
          credit ? (
            <>
              {schoolCount - 1} schools and units · publications credited through the staff roster · labels can be
              renamed in <Link href="/admin/hierarchy">Admin</Link>
            </>
          ) : (
            <>
              {schoolCount} units · {unitCount} departments and centres · labels can be renamed in{' '}
              <Link href="/admin/hierarchy">Admin</Link>
            </>
          )
        }
      >
        {credit ? <CreditMethod credit={credit} /> : <DepartmentMethod />}
      </OrganisationExplorer>

      {credit && (
        <Card className="mt-24" aria-labelledby="credit-title">
          <CardHeader
            id="credit-title"
            title="Publications by school"
            subtitle="Publications credited to each school in this period · totals overlap because one publication can credit several schools"
          />
          <BarList items={credit.bars} max={credit.bars[0]?.value || 1} unit="publications" />
          <hr className="divider" />
          <DataTable
            caption="Publications credited to each school, through the staff roster and including department evidence"
            columns={COLUMNS}
            rows={credit.rows}
            variant="roomy"
          />
        </Card>
      )}
    </>
  );
}
