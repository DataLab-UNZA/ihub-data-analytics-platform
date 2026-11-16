import Link from 'next/link';
import AddSourceProgress from '@/components/features/data/AddSourceProgress';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import ChoiceGroup from '@/components/ui/ChoiceGroup';
import Grid from '@/components/ui/Grid';
import { sourceTypes } from '@/data/data-ops';

export const metadata = {
  title: 'Add a data source · Choose source',
  description: 'Step 1 of 4: choose the type of data source to connect.',
};

export default function ChooseSourcePage() {
  return (
    <>
      <PageHeader title="Add a data source" />
      <AddSourceProgress current={1} />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="type-title">
          <CardHeader
            id="type-title"
            title="Choose a source type"
            subtitle="Connect using a supported connector or a structured import"
          />
          <form action="/data-sources/add/connect" method="get">
            <ChoiceGroup legend="Source type" name="source" items={sourceTypes} defaultValue="repository" />
            <div className="align-end mt-48">
              <Button size="md" type="submit">
                Continue
              </Button>
            </div>
          </form>
        </Card>

        <Card aria-labelledby="before-title">
          <CardHeader id="before-title" title="Before you connect" className="mb-32" />
          <h3>Keep the source of truth intact</h3>
          <p className="text-muted mt-24">
            iHub reads records from your systems. Reconciliation never changes the original source.
          </p>
          <h3 className="subhead--plain mt-48 text-md">You’ll need</h3>
          <ul className="bullets mt-16">
            <li>Source endpoint or export</li>
            <li>Organisation identifier</li>
            <li>Access credentials, if required</li>
            <li>A data steward for alerts</li>
          </ul>
          <p className="mt-48">
            <Link href="/admin/users">Admin access required</Link>
          </p>
        </Card>
      </Grid>
    </>
  );
}
