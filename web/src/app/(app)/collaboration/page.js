import Link from 'next/link';
import WorldMap from '@/components/charts/WorldMap';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import KpiGrid from '@/components/ui/Kpi';
import { readFilters } from '@/lib/filters-server';
import { loadCollaboration } from '@/services/research';

export const metadata = {
  title: 'Collaboration',
  description: 'Co-authored outputs by affiliation country and partner organisation.',
};

const COLUMNS = [
  { key: 'partner', header: 'Partner', rowHeader: true, href: () => '/publications' },
  { key: 'country', header: 'Country' },
  { key: 'outputs', header: 'Outputs' },
];

export default async function CollaborationPage() {
  const data = await loadCollaboration(await readFilters());

  return (
    <>
      <PageHeader title="Collaboration" />
      <KpiGrid items={data.kpis} titled label="Collaboration summary" />

      <Grid variant="main-aside">
        <Card aria-labelledby="where-title">
          <CardHeader
            id="where-title"
            title="Where collaboration happens"
            subtitle="Select a country to view the source-linked outputs"
          />
          <WorldMap pins={data.pins} href="/publications" wide />
          <p className="card__foot mt-64">Co-authored outputs by affiliation country</p>
        </Card>

        <Card aria-labelledby="partners-title">
          <CardHeader id="partners-title" title="Partner organisations" subtitle="Most co-authored institutions" />
          <DataTable
            caption="Partner organisations, most co-authored first"
            columns={COLUMNS}
            rows={data.partners}
            variant="roomy"
          />
          <p className="card__foot mt-32">
            <Link href="/publications">View all publications →</Link>
          </p>
        </Card>
      </Grid>
    </>
  );
}
