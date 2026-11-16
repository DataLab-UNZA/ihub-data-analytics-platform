import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { formatNumber } from '@/lib/format';
import { formatRefreshed } from '@/lib/shell-data';
import { loadSources } from '@/services/research';

export const metadata = {
  title: 'Data sources',
  description: 'Connected sources, how many publications each holds, and the refresh policy.',
};

const COLUMNS = [
  { key: 'source', header: 'Source', rowHeader: true, href: () => '/coverage' },
  { key: 'kind', header: 'Kind' },
  { key: 'publications', header: 'Publications' },
  { key: 'share', header: 'Share of corpus' },
];

export default async function DataSourcesPage() {
  const data = await loadSources();
  const lastRun = formatRefreshed(data.lastRun);

  return (
    <>
      <PageHeader title="Data sources" />

      <Card className="mb-24" aria-labelledby="connected-title">
        <div className="card__head--split">
          <div>
            <h2 className="card__title" id="connected-title">
              Connected sources
            </h2>
            <p className="card__sub">
              Weekly refresh · Mondays at 06:00 CAT · last pipeline run: {lastRun ?? 'not recorded in this database'}
            </p>
          </div>
          <Button size="md" href="/data-sources/add/choose">
            Add source
          </Button>
        </div>
      </Card>

      <Card className="mb-24" aria-labelledby="health-title">
        <CardHeader
          id="health-title"
          title="Sources in the research mart"
          subtitle={`${formatNumber(data.publications)} de-duplicated publications · source counts overlap`}
        />
        <DataTable caption="Publications held by each connected source" columns={COLUMNS} rows={data.rows} variant="roomy" />
      </Card>

      <Card aria-labelledby="policy-title">
        <h2 className="card__title" id="policy-title">
          Refresh policy &amp; alerts
        </h2>
        <h3 className="mt-40 subhead--lg">One trusted snapshot each week</h3>
        <p className="text-muted mt-16 text-md">
          If a source fails, keep the last successful records, show the source’s last success date, and notify the data
          steward.
        </p>
        <p className="mt-24 text-sm">
          <Link href="/notifications">Alert recipients: Workspace admin, Data librarian · Email + in-app</Link>{' '}
          <Link className="ml-16" href="/notifications">
            Manage alerts →
          </Link>
        </p>
      </Card>
    </>
  );
}
