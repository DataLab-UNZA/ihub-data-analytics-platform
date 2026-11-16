import Link from 'next/link';
import AddSourceProgress from '@/components/features/data/AddSourceProgress';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { fieldMappings } from '@/data/data-ops';

export const metadata = {
  title: 'Add a data source · Map fields',
  description: 'Step 3 of 4: map source fields to the shared iHub data model.',
};

const COLUMNS = [
  { key: 'sourceField', header: 'Source field', rowHeader: true, href: (row) => `#field-${row.id}` },
  {
    key: 'ihubField',
    header: 'iHub field',
    render: (row) => (
      <>
        {row.ihubField}
        {row.required && (
          <>
            {' '}
            <abbr title="Required">*</abbr>
          </>
        )}
      </>
    ),
  },
  { key: 'example', header: 'Example value' },
  { key: 'validation', header: 'Validation' },
];

export default function MapFieldsPage() {
  return (
    <>
      <PageHeader title="Add a data source" />
      <AddSourceProgress current={3} />

      <Card aria-labelledby="map-title">
        <CardHeader
          id="map-title"
          title="Map source fields"
          subtitle="Required fields are marked · sample values shown before import"
        />
        <form action="/data-sources/add/review" method="get">
          <DataTable
            caption="Mapping of source fields to iHub fields"
            columns={COLUMNS}
            rows={fieldMappings}
            variant="roomy"
          />
          <p className="text-muted mt-24 text-sm">
            Unmapped values remain Unknown. Unit assignments can be reviewed in <Link href="/data-quality">Data quality</Link>.
          </p>
          <div className="align-end mt-16">
            <Button size="md" type="submit">
              Continue to review
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
