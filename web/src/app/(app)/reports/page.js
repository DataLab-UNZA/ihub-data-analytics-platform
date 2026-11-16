import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import ChoiceGroup from '@/components/ui/ChoiceGroup';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import { recentReports, reportFormats } from '@/data/workspace';

export const metadata = {
  title: 'Reports',
  description: 'Generate or schedule executive reports that respect current filters and role permissions.',
};

const COLUMNS = [
  { key: 'report', header: 'Report', rowHeader: true, href: () => '/reports' },
  { key: 'format', header: 'Format' },
  { key: 'generated', header: 'Generated', render: (row) => <time dateTime={row.generatedIso}>{row.generated}</time> },
  { key: 'status', header: 'Status' },
  { key: 'action', header: 'Action', render: () => <Link href="/reports">Download →</Link> },
];

export default function ReportsPage() {
  return (
    <>
      <PageHeader title="Reports" aside="Illustrative data · not connected yet" />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="create-title">
          <CardHeader
            id="create-title"
            title="Create an executive report"
            subtitle="Exports respect your current filters and role permissions"
            className="mb-32"
          />
          <form action="/reports" method="post">
            <ChoiceGroup legend="Format" name="format" items={reportFormats} defaultValue="pdf" row visibleLegend />
            <p className="text-muted mt-32 text-sm">Include: Overview, unit comparison, coverage, source notes</p>
            <Button className="mt-32" size="lg" type="submit">
              Generate report
            </Button>
          </form>
        </Card>

        <Card aria-labelledby="delivery-title">
          <CardHeader id="delivery-title" title="Delivery" subtitle="Schedule or download once" className="mb-32" />
          <p className="text-md fw-500">Weekly · Monday 08:00 CAT</p>
          <p className="text-muted mt-16 text-sm">Recipients: executive group</p>
          <p className="mt-24 text-sm">
            <Link href="/data-sources">
              Data as of <time dateTime="2026-11-16">16 Nov 2026</time>
            </Link>
          </p>
          <Button className="mt-32" variant="secondary" block>
            Schedule delivery
          </Button>
        </Card>
      </Grid>

      <Card className="mt-24" aria-labelledby="recent-title">
        <CardHeader
          id="recent-title"
          title="Recent reports"
          subtitle="Generated snapshots are versioned with their filters"
        />
        <DataTable caption="Recently generated reports" columns={COLUMNS} rows={recentReports} variant="roomy" />
      </Card>
    </>
  );
}
