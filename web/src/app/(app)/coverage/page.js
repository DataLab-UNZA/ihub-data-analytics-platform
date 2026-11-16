import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import BarList from '@/components/ui/BarList';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import KpiGrid from '@/components/ui/Kpi';
import { readFilters } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadCoverage } from '@/services/research';

export const metadata = {
  title: 'Source coverage',
  description: 'How many publications each source holds, and which are in one source but not another.',
};

const COLUMNS = [
  { key: 'title', header: 'Publication', rowHeader: true, href: (row) => `/publications/${row.key}` },
  { key: 'year', header: 'Year' },
  { key: 'foundIn', header: 'Found in' },
  { key: 'action', header: 'Action', render: (row) => <Link href={`/publications/${row.key}`}>Verify record →</Link> },
];

export default async function CoveragePage() {
  const data = await loadCoverage(await readFilters());
  const [repositoryGap, ...otherGaps] = data.gaps;

  return (
    <>
      <PageHeader title="Source coverage" />
      <KpiGrid items={data.kpis} titled label="Source totals" />

      <Grid variant="halves">
        <Card aria-labelledby="corpus-title">
          <CardHeader
            id="corpus-title"
            title="One corpus, multiple sources"
            subtitle={`${formatNumber(data.publications)} unique publications after reconciliation`}
            className="mb-32"
          />
          <BarList items={data.sourceBars} max={data.publications || 1} unit="publications" />
        </Card>

        <Card aria-labelledby="opportunity-title">
          <CardHeader
            id="opportunity-title"
            title="Repository opportunity"
            subtitle="Source coverage is not a judgement of research quality"
            className="mb-40"
          />
          <p className="big-figure big-figure--xl">{formatNumber(repositoryGap.count)}</p>
          <p className="text-muted text-lg mt-8">outputs not found in the repository</p>
          <p className="text-muted text-sm mt-32">
            “Not found” does not prove an output is absent. Verify source matches before follow-up.
          </p>
        </Card>
      </Grid>

      {[repositoryGap, ...otherGaps].map((gap, index) => (
        <Card className={index ? 'mt-24' : undefined} aria-labelledby={`gap-${gap.in_source}-${gap.missing_from}`} key={gap.title}>
          <CardHeader
            id={`gap-${gap.in_source}-${gap.missing_from}`}
            title={gap.title}
            subtitle={`${formatNumber(gap.count)} publications · ${gap.purpose}`}
          />
          {gap.rows.length === 0 ? (
            <p className="text-muted">None in this period.</p>
          ) : (
            <DataTable caption={gap.title} columns={COLUMNS} rows={gap.rows} variant="roomy" />
          )}
          {gap.count > gap.rows.length && (
            <p className="card__foot">
              Showing the first {gap.rows.length} of {formatNumber(gap.count)}.
            </p>
          )}
        </Card>
      ))}
    </>
  );
}
