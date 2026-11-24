import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import ExternalLink from '@/components/ui/ExternalLink';
import { Field, Select, Textarea } from '@/components/ui/Form';
import Grid, { GridStack } from '@/components/ui/Grid';
import Pager from '@/components/ui/Pager';
import { correctionTypes } from '@/data/members';
import { readFilters, periodLabel } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadMember } from '@/services/members';

export const metadata = {
  title: 'Member profile',
  description: 'Authorised member profile with linked publications and a record correction form.',
};

const COLUMNS = [
  { key: 'title', header: 'Publication', rowHeader: true, href: (row) => `/publications/${row.key}` },
  { key: 'year', header: 'Year' },
  { key: 'type', header: 'Type' },
  { key: 'source', header: 'Source' },
];

const first = (value) => (Array.isArray(value) ? value[0] : value);

function unitLabel(member) {
  if (!member.fellow) return member.school ?? 'No school on the roster';
  return member.school ? `${member.school} (staff development fellow)` : 'Staff development fellow, no school on the roster';
}

export default async function MemberProfilePage({ params, searchParams }) {
  const { id } = await params;
  const page = Math.max(1, Number.parseInt(first((await searchParams).page) ?? '1', 10) || 1);
  const filters = await readFilters();
  const data = await loadMember(id, filters, page);
  const { member } = data;
  const fullName = [member.title, member.name].filter(Boolean).join(' ');
  const href = (target) => (target > 1 ? `/members/${id}?page=${target}` : `/members/${id}`);
  const from = (data.page - 1) * data.page_size + 1;
  const to = from + data.rows.length - 1;
  const period = /^\d{4}$/.test(filters.period) ? periodLabel({ start: filters.period, end: filters.period }) : 'all years';

  return (
    <>
      <PageHeader title="Member profile" />

      <Grid variant="main-aside" start>
        <GridStack>
          <Card aria-labelledby="member-title">
            <CardHeader
              id="member-title"
              title={fullName}
              subtitle={`Member profile · ${unitLabel(member)}`}
              className="mb-24"
            />
            <div className="meta-grid">
              <div>
                <p>
                  <Link href="/members">Authorised Executive view</Link>
                </p>
                <p className="meta-label mt-24">ORCID</p>
                <p className="mt-8">
                  {member.orcid_url ? (
                    <ExternalLink href={member.orcid_url}>Linked · {member.orcid}</ExternalLink>
                  ) : (
                    'Unknown · no ORCID iD found for this author'
                  )}
                </p>
              </div>
              <div>
                <p className="big-figure">
                  {formatNumber(member.publications)} output{member.publications === 1 ? '' : 's'}
                </p>
                <p className="text-muted mt-8">
                  {formatNumber(member.open_access)} open access · {formatNumber(member.citations)} citations · {period}
                </p>
              </div>
            </div>
          </Card>

          <Card aria-labelledby="linked-title">
            <CardHeader id="linked-title" title="Linked publications" subtitle="Newest first · no individual comparisons" />
            {data.publications.length === 0 ? (
              <p className="text-muted">No linked publications in this period.</p>
            ) : (
              <DataTable
                caption={`Publications linked to ${fullName}, newest first`}
                columns={COLUMNS}
                rows={data.publications}
                variant="roomy"
              />
            )}
            <Pager
              label="Linked publications pagination"
              summary={
                data.total
                  ? `${formatNumber(from)}–${formatNumber(to)} of ${formatNumber(data.total)} publications`
                  : '0 publications'
              }
              previous={data.page > 1 ? { label: '← Previous', href: href(data.page - 1) } : undefined}
              pages={[{ label: String(data.page), href: href(data.page), current: true }]}
              next={data.page < data.pages ? { label: 'Next →', href: href(data.page + 1) } : undefined}
            />
          </Card>
        </GridStack>

        <Card aria-labelledby="correct-title">
          <CardHeader id="correct-title" title="Correct a record" subtitle="Submit a correction for librarian review" />
          <form className="form-grid" action={`/members/${id}`} method="post">
            <div>
              <p className="legend-label" id="record-label">
                Record
              </p>
              <p className="panel" aria-labelledby="record-label">
                {data.publications[0] ? (
                  <Link href={`/publications/${data.publications[0].key}`}>{data.publications[0].title}</Link>
                ) : (
                  'No record to correct'
                )}
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
            <Button block type="submit" disabled>
              Submit correction
            </Button>
            <p className="text-muted text-small">Corrections are not connected yet · visible to you and data stewards only</p>
          </form>
        </Card>
      </Grid>
    </>
  );
}
