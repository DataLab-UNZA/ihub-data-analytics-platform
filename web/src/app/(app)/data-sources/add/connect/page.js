import AddSourceProgress from '@/components/features/data/AddSourceProgress';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import { Field, Input, Select } from '@/components/ui/Form';
import Grid from '@/components/ui/Grid';
import StatusText from '@/components/ui/StatusText';
import { authenticationOptions } from '@/data/data-ops';

export const metadata = {
  title: 'Add a data source · Connect',
  description: 'Step 2 of 4: enter the repository endpoint and test the connection.',
};

export default function ConnectSourcePage() {
  return (
    <>
      <PageHeader title="Add a data source" />
      <AddSourceProgress current={2} />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="connect-title">
          <CardHeader
            id="connect-title"
            title="Connect your repository"
            subtitle="Credentials are stored securely and never displayed after saving"
          />
          <form className="form-grid" action="/data-sources/add/map-fields" method="get">
            <Field id="source-name" label="Source name">
              <Input id="source-name" name="name" type="text" defaultValue="UNZA institutional repository" required />
            </Field>
            <Field id="source-endpoint" label="OAI-PMH endpoint">
              <Input
                id="source-endpoint"
                name="endpoint"
                type="url"
                defaultValue="https://repository.example.org/oai"
                aria-describedby="endpoint-hint"
                required
              />
            </Field>
            <Field id="source-auth" label="Authentication">
              <Select id="source-auth" name="auth" options={authenticationOptions} />
            </Field>
            <p className="field__hint" id="endpoint-hint">
              Example endpoint · replace before connecting
            </p>
            <div>
              <Button variant="secondary" size="sm">
                Test connection
              </Button>
              <StatusText className="mt-16" role="status">
                Connection successful · metadata format: oai_dc
              </StatusText>
            </div>
            <div className="align-end">
              <Button size="md" type="submit">
                Continue
              </Button>
            </div>
          </form>
        </Card>

        <Card aria-labelledby="check-title">
          <CardHeader id="check-title" title="Connection check" className="mb-32" />
          <ul className="check-list">
            <li>Endpoint reachable</li>
            <li>OAI-PMH supported</li>
            <li>Read-only access verified</li>
          </ul>
          <p className="meta-label mt-48">Expected records</p>
          <p className="big-figure mt-16">14,620</p>
          <p className="text-muted mt-48">Next: map source fields to iHub’s shared data model.</p>
        </Card>
      </Grid>
    </>
  );
}
