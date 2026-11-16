import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import ExternalLink from '@/components/ui/ExternalLink';
import Grid from '@/components/ui/Grid';
import KpiGrid from '@/components/ui/Kpi';
import LinkList from '@/components/ui/LinkList';
import StatusText from '@/components/ui/StatusText';
import { qualityKpis, reviewQueue } from '@/data/data-ops';

export const metadata = {
  title: 'Data quality',
  description: 'Librarian review queue for flagged matches, unassigned outputs and possible duplicates.',
};

const COLUMNS = [
  { key: 'item', header: 'Item', rowHeader: true, href: () => '#flagged-match' },
  { key: 'issue', header: 'Issue' },
  { key: 'action', header: 'Action', href: () => '#flagged-match' },
];

export default function DataQualityPage() {
  return (
    <>
      <PageHeader title="Data quality" aside="Illustrative data · not connected yet" />
      <KpiGrid items={qualityKpis} titled label="Data quality summary" />

      <Grid variant="main-aside" start>
        <Card aria-labelledby="queue-title">
          <CardHeader
            id="queue-title"
            title="Review queue"
            subtitle="Librarian / Admin access · decisions preserve an audit history"
          />
          <DataTable caption="Items awaiting review" columns={COLUMNS} rows={reviewQueue} variant="roomy" />
        </Card>

        <Card id="flagged-match" aria-labelledby="match-title">
          <CardHeader id="match-title" title="Review a flagged match" subtitle="Community health systems · 2 source records" />
          <LinkList
            divided
            items={[
              {
                label: 'OpenAlex',
                children: (
                  <>
                    <ExternalLink href="https://openalex.org/">OpenAlex</ExternalLink>
                    <p className="card__sub mt-16">Year: 2026 · author: C. Banda</p>
                  </>
                ),
              },
              {
                label: 'ORCID',
                children: (
                  <>
                    <ExternalLink href="https://orcid.org/">ORCID</ExternalLink>
                    <p className="card__sub mt-16">Year: 2026 · linked author ORCID</p>
                  </>
                ),
              },
            ]}
          />
          <StatusText tone="warn" className="mt-32 text-md">
            Same title · author affiliation differs
          </StatusText>
          <p className="text-muted mt-16">
            Review the original records before merging. Split if they represent distinct outputs.
          </p>
          <div className="stack stack--sm mt-48">
            <Button block>Approve match</Button>
            <Button variant="secondary" block>
              Split into two records
            </Button>
          </div>
          <p className="text-muted text-small mt-32">Decision and reason will be logged.</p>
        </Card>
      </Grid>
    </>
  );
}
