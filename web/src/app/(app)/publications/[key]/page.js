import { notFound } from 'next/navigation';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import ExternalLink from '@/components/ui/ExternalLink';
import Grid, { GridStack } from '@/components/ui/Grid';
import LinkList from '@/components/ui/LinkList';
import { ApiError, apiGet } from '@/lib/api';
import { capitalise, formatNumber } from '@/lib/format';
import { describeMatchRule } from '@/lib/match-rules';

export const metadata = {
  title: 'Publication record',
  description: 'A single reconciled publication record with source evidence and match reasoning.',
};

const COLUMNS = [
  { key: 'field', header: 'Metadata', rowHeader: true },
  { key: 'value', header: 'Value' },
];

async function loadRecord(key) {
  try {
    return await apiGet(`/api/publications/${encodeURIComponent(key)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

export default async function PublicationRecordPage({ params }) {
  const { key } = await params;
  const record = await loadRecord(key);

  const rows = [
    { id: 'year', field: 'Year / type', value: `${record.year} · ${record.type}` },
    { id: 'venue', field: 'Journal / venue', value: record.venue },
    {
      id: 'doi',
      field: 'DOI',
      value: record.doi_url ? <ExternalLink href={record.doi_url}>{record.doi}</ExternalLink> : (record.doi ?? 'Unknown'),
    },
    { id: 'units', field: 'Unit', value: record.units.length ? record.units.join(' · ') : 'Unknown' },
    { id: 'oa', field: 'Open access', value: capitalise(record.oa_status) },
    { id: 'cites', field: 'Citations', value: formatNumber(record.cited_by_count) },
  ];
  const mergedRecords = record.sources.length;

  return (
    <>
      <PageHeader title="Publication record" />

      <Grid variant="main-aside" start>
        <GridStack>
          <Card as="article" aria-labelledby="record-title">
            <CardHeader
              id="record-title"
              title={record.title}
              subtitle={`Publication record · ${record.n_authors} author${record.n_authors === 1 ? '' : 's'}`}
              className="mb-24"
            />
            <p className="mb-32">
              {record.authors.length === 0
                ? 'No authors listed'
                : record.authors.map((author, index) => (
                    <span key={`${author.name}-${index}`}>
                      {index > 0 && ' · '}
                      {author.orcid_url ? <ExternalLink href={author.orcid_url}>{author.name}</ExternalLink> : author.name}
                    </span>
                  ))}
            </p>
            <DataTable caption="Publication metadata" columns={COLUMNS} rows={rows} variant="roomy" />
          </Card>

          <Card aria-labelledby="provenance-title">
            <CardHeader id="provenance-title" title="Provenance" className="mb-24" />
            <p className="text-muted text-md">
              This record merges {mergedRecords} source record{mergedRecords === 1 ? '' : 's'}. Source values are kept
              in the pipeline&rsquo;s raw layer; the mart shows one de-duplicated publication.
            </p>
          </Card>
        </GridStack>

        <GridStack>
          <Card aria-labelledby="sources-title">
            <CardHeader id="sources-title" title="Sources found in" subtitle="Evidence is kept for every merged record" />
            <LinkList
              divided
              items={record.sources.map((source, index) => ({
                label: `${source.source}-${index}`,
                children: source.url ? (
                  <ExternalLink href={source.url}>{source.source} · View original</ExternalLink>
                ) : (
                  <span>{source.source} · no public link</span>
                ),
              }))}
            />
          </Card>

          <Card aria-labelledby="match-title">
            <CardHeader id="match-title" title="Why these records match" subtitle="How the pipeline matched them" />
            <ul className="stack stack--sm">
              {record.sources.map((source, index) => (
                <li key={`${source.source}-${index}`}>
                  <h3 className="subhead--plain text-md">{source.source}</h3>
                  <p className="text-muted mt-8 text-sm">{describeMatchRule(source.match_rule)}</p>
                </li>
              ))}
            </ul>
            <Button className="mt-40" variant="secondary" href="/data-quality" block>
              Report an issue
            </Button>
          </Card>
        </GridStack>
      </Grid>
    </>
  );
}
