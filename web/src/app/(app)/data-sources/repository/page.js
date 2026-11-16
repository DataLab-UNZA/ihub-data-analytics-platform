import PageHeader from '@/components/layout/PageHeader';
import Alert from '@/components/ui/Alert';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import StatusText from '@/components/ui/StatusText';
import { failureDetails } from '@/data/data-ops';

export const metadata = {
  title: 'Repository connection',
  description: 'Failure details for the repository connector, with recovery actions. No data was deleted.',
};

const COLUMNS = [
  { key: 'detail', header: 'Run detail', rowHeader: true, href: () => '/data-sources' },
  { key: 'value', header: 'Value' },
];

export default function RepositoryConnectionPage() {
  return (
    <>
      <PageHeader title="Repository connection" />

      <Alert
        id="failed-title"
        variant="card"
        role="alert"
        title="Refresh failed · action required"
        emphasis={
          <>
            Showing last successful records from <time dateTime="2026-11-09">9 Nov 2026</time>. Other sources are
            unaffected.
          </>
        }
      >
        Repository could not be refreshed on <time dateTime="2026-11-16T06:08">16 Nov 2026 at 06:08 CAT</time>
      </Alert>

      <Grid variant="main-aside" start>
        <Card aria-labelledby="details-title">
          <CardHeader id="details-title" title="Repository connection" subtitle="Admin view · failure details" />
          <DataTable caption="Details of the failed run" columns={COLUMNS} rows={failureDetails} variant="roomy" />
          <div className="btn-row mt-48">
            <Button size="lg" href="/data-sources/add/connect">
              Update credentials
            </Button>
            <Button variant="secondary" size="md" href="/data-sources/repository">
              Retry now
            </Button>
          </div>
        </Card>

        <Card aria-labelledby="alerts-title">
          <CardHeader id="alerts-title" title="Failure alerts" className="mb-32" />
          <h3>Email + in-app notification</h3>
          <p className="text-muted mt-24">Sent to Workspace admin and Data librarian.</p>
          <h3 className="subhead--plain mt-48 text-md">Troubleshooting</h3>
          <ol className="numbered mt-16">
            <li>Confirm credentials</li>
            <li>Verify endpoint permissions</li>
            <li>Retry the source refresh</li>
          </ol>
          <StatusText className="mt-48 text-md">No data was deleted</StatusText>
          <p className="text-muted mt-16 text-sm">Existing records remain available with a stale-source indicator.</p>
        </Card>
      </Grid>
    </>
  );
}
