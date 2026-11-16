import Link from 'next/link';
import BarList from '@/components/ui/BarList';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import KpiGrid from '@/components/ui/Kpi';
import Alert from '@/components/ui/Alert';
import LineChart from '@/components/charts/LineChart';
import WorldMap from '@/components/charts/WorldMap';
import PageHeader from '@/components/layout/PageHeader';
import { formatNumber, pointsChange } from '@/lib/format';

const JOURNAL_COLUMNS = [
  { key: 'journal', header: 'Journal', rowHeader: true, href: () => '/journals' },
  { key: 'outputs', header: 'Outputs' },
];

/**
 * Executive overview, drawn from the data returned by services/overview.js.
 * With `showStale` it adds the "weekly refresh is overdue" banner above the
 * last trusted snapshot.
 */
export default function OverviewDashboard({ data, showStale = false }) {
  const { years, stale } = data;
  const period = years.start === years.end ? `${years.start}` : `${years.start} to ${years.end}`;

  return (
    <>
      <PageHeader
        title="Your organisation, at a glance"
        aside={showStale ? 'Last trusted snapshot · source refresh overdue' : undefined}
      />

      {showStale && (
        <Alert id="stale-title" variant="banner" role="status" title="Data may be out of date · weekly refresh is overdue">
          Last successful refresh: {stale.lastRun ?? 'not recorded'} · Showing the last trusted snapshot.{' '}
          <Link href="/data-sources">View source status →</Link>
        </Alert>
      )}

      <KpiGrid items={data.kpis} />

      <Grid variant="main-aside">
        <Card aria-labelledby="output-title">
          <CardHeader
            id="output-title"
            title="Research output over time"
            subtitle="Outputs by year · select a point to see the underlying records"
          />
          <LineChart
            id="overview-output"
            caption={`Research output per year, ${period}`}
            data={data.series}
            max={data.scale.max}
            step={data.scale.step}
            drillHref="/publications"
          />
        </Card>

        <Card aria-labelledby="units-title">
          <CardHeader
            id="units-title"
            title="Outputs by unit"
            subtitle={`${data.schoolCount} units with output · a publication counts once in each school`}
          />
          <BarList items={data.schools} max={data.schoolMax} />
        </Card>
      </Grid>

      <Grid variant="trio">
        <Card aria-labelledby="journals-title">
          <CardHeader
            id="journals-title"
            title="Top journals by output"
            subtitle={
              <>
                Busiest venues · <Link href="/journals">view all journals →</Link>
              </>
            }
          />
          <DataTable caption="Top journals by output" columns={JOURNAL_COLUMNS} rows={data.venues} />
        </Card>

        <Card aria-labelledby="map-title">
          <CardHeader id="map-title" title="Collaboration map" subtitle="Co-authored outputs by country" />
          <WorldMap pins={data.pins} href="/collaboration" />
          {data.topPartner && (
            <p className="card__foot">
              <Link href="/collaboration">
                {data.topPartner.name} · {formatNumber(data.topPartner.publications)} collaborations
              </Link>
            </p>
          )}
          <p className="card__sub">Select a country to explore records</p>
        </Card>

        <Card aria-labelledby="changes-title">
          <CardHeader id="changes-title" title="What changed" subtitle="Insights from your refreshed sources" />
          <article>
            <p className="eyebrow">Open access</p>
            <h3>
              {data.oaChange === null || data.oaChange >= 0 ? 'More research is accessible' : 'Open access share fell'}
            </h3>
            <p className="card__sub">
              {data.oaChange === null
                ? `${(data.oaShare * 100).toFixed(1)}% of outputs in this period are open access.`
                : `OA share changed by ${pointsChange(data.oaShare, data.oaShare - data.oaChange)} compared with the previous period.`}
            </p>
          </article>
          <hr className="divider" />
          <article>
            <h3>Repository opportunity</h3>
            <p className="card__sub">
              <Link href="/coverage">
                {formatNumber(data.missingFromRepository)} outputs are not yet found in the repository. Review
                coverage →
              </Link>
            </p>
          </article>
        </Card>
      </Grid>
    </>
  );
}
