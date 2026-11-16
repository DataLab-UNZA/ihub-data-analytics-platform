import Link from 'next/link';
import AddSourceProgress from '@/components/features/data/AddSourceProgress';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import { reviewSettings } from '@/data/data-ops';

export const metadata = {
  title: 'Add a data source · Review',
  description: 'Step 4 of 4: review the connector settings and schedule the first run.',
};

const COLUMNS = [
  { key: 'setting', header: 'Setting', rowHeader: true, href: (row) => row.href },
  { key: 'value', header: 'Value' },
];

export default function ReviewSourcePage() {
  return (
    <>
      <PageHeader title="Add a data source" />
      <AddSourceProgress current={4} />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="review-title">
          <CardHeader id="review-title" title="Review & schedule" subtitle="Your source is not added until you confirm" />
          <form action="/data-sources" method="get">
            <DataTable
              caption="Connector settings to confirm"
              columns={COLUMNS}
              rows={reviewSettings}
              variant="roomy"
            />
            <div className="align-end mt-48">
              <Button size="md" type="submit">
                Add source &amp; run
              </Button>
            </div>
          </form>
        </Card>

        <Card aria-labelledby="safeguards-title">
          <CardHeader id="safeguards-title" title="Import safeguards" className="mb-32" />
          <h3>Read only. Fully traceable.</h3>
          <p className="text-muted mt-24">
            Every record retains its source ID, ingestion date and matching decision.
          </p>
          <p className="text-muted mt-48">
            Possible duplicates and uncertain matches go to the review queue, not directly into a merged record.
          </p>
          <h3 className="subhead--plain mt-48 text-md">After confirmation</h3>
          <p className="text-muted mt-16">
            The first run begins in the background. You can follow its progress in <Link href="/data-sources">Data sources</Link>.
          </p>
        </Card>
      </Grid>
    </>
  );
}
