import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import KpiGrid from '@/components/ui/Kpi';
import { readFilters } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadJournals } from '@/services/research';

export const metadata = {
  title: 'Journals',
  description: 'Venues with the most UNZA publications, with linked output counts and open access share.',
};

const COLUMNS = [
  { key: 'journal', header: 'Journal', rowHeader: true, href: () => '/publications' },
  { key: 'outputs', header: 'Outputs', href: () => '/publications' },
  { key: 'oaShare', header: 'OA share' },
  { key: 'citations', header: 'Citations' },
];

export default async function JournalsPage() {
  const data = await loadJournals(await readFilters());

  return (
    <>
      <PageHeader title="Journals" />
      <KpiGrid items={data.kpis} titled label="Journal summary" />

      <Card aria-labelledby="directory-title">
        <CardHeader
          id="directory-title"
          title="Journals directory"
          subtitle="Busiest venues first · unknown venues are not listed · ISSNs are not in the mart yet"
        />
        <DataTable caption="Venues, busiest first" columns={COLUMNS} rows={data.rows} variant="roomy" />
        <div className="pager">
          <p>
            Showing {formatNumber(data.shown)} of {formatNumber(data.venuesInPeriod)} venues
          </p>
        </div>
      </Card>
    </>
  );
}
