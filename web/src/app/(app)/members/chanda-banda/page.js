import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { Field, Select, Textarea } from '@/components/ui/Form';
import Grid, { GridStack } from '@/components/ui/Grid';
import ExternalLink from '@/components/ui/ExternalLink';
import { correctionTypes, linkedPublications } from '@/data/members';

export const metadata = {
  title: 'Member profile',
  description: 'Authorised member profile with linked publications and a record correction form.',
};

const COLUMNS = [
  { key: 'title', header: 'Publication', rowHeader: true, href: () => '/publications/example-record' },
  { key: 'year', header: 'Year' },
  { key: 'source', header: 'Source' },
];

export default function MemberProfilePage() {
  return (
    <>
      <PageHeader title="Member profile" aside="Illustrative data · not connected yet" />

      <Grid variant="main-aside" start>
        <GridStack>
          <Card aria-labelledby="member-title">
            <CardHeader
              id="member-title"
              title="Chanda Banda"
              subtitle="Member profile · Public Health / School of Medicine"
              className="mb-24"
            />
            <div className="meta-grid">
              <div>
                <p>
                  <Link href="/members">Authorised Executive view</Link>
                </p>
                <p className="meta-label mt-24">ORCID</p>
                <p className="mt-8">
                  <ExternalLink href="https://orcid.org/">Linked · view source profile</ExternalLink>
                </p>
              </div>
              <div>
                <p className="big-figure">48 outputs</p>
                <p className="text-muted mt-8">25 open access · 362 citations</p>
              </div>
            </div>
          </Card>

          <Card aria-labelledby="linked-title">
            <CardHeader id="linked-title" title="Linked publications" subtitle="Newest first · no individual comparisons" />
            <DataTable
              caption="Publications linked to Chanda Banda, newest first"
              columns={COLUMNS}
              rows={linkedPublications}
              variant="roomy"
            />
          </Card>
        </GridStack>

        <Card aria-labelledby="correct-title">
          <CardHeader id="correct-title" title="Correct a record" subtitle="Submit a correction for librarian review" />
          <form className="form-grid" action="/members/chanda-banda" method="post">
            <div>
              <p className="legend-label" id="record-label">
                Record
              </p>
              <p className="panel" aria-labelledby="record-label">
                <Link href="/publications/example-record">Strengthening community health systems in Zambia</Link>
              </p>
            </div>
            <Field id="correction-type" label="What needs correcting?">
              <Select id="correction-type" name="correction-type" options={correctionTypes} />
            </Field>
            <Field id="correction-details" label="Details">
              <Textarea id="correction-details" name="details" placeholder="Add context or a source link…" />
            </Field>
            <p className="text-muted text-sm">
              Corrections never edit original source records. You’ll be notified when reviewed.
            </p>
            <Button block type="submit">
              Submit correction
            </Button>
            <p className="text-muted text-small">Visible to you and data stewards only</p>
          </form>
        </Card>
      </Grid>
    </>
  );
}
