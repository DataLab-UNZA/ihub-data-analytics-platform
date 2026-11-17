import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import ExternalLink from '@/components/ui/ExternalLink';
import { SelectLink } from '@/components/ui/Form';
import Pager from '@/components/ui/Pager';
import { readFilters } from '@/lib/filters-server';
import { formatNumber } from '@/lib/format';
import { loadMembers, memberPageHref, readMemberQuery } from '@/services/members';

export const metadata = {
  title: 'Members',
  description: 'Authorised, alphabetical member directory. Individuals are never ranked.',
};

const ORCID_OPTIONS = [
  ['', 'ORCID: All'],
  ['linked', 'ORCID: Linked'],
  ['unknown', 'ORCID: Unknown'],
];

const COLUMNS = [
  { key: 'title', header: 'Title' },
  { key: 'member', header: 'Member A–Z', rowHeader: true, href: (row) => `/members/${row.id}` },
  { key: 'unit', header: 'Unit' },
  {
    key: 'orcid',
    header: 'ORCID',
    render: (row) => (row.orcidUrl ? <ExternalLink href={row.orcidUrl}>Linked</ExternalLink> : 'Unknown'),
  },
  { key: 'records', header: 'Records' },
  {
    key: 'access',
    header: 'Access',
    render: (row) => <Link href={`/members/${row.id}`}>View profile →</Link>,
  },
];

export default async function MembersPage({ searchParams }) {
  const query = readMemberQuery(await searchParams);
  const data = await loadMembers(await readFilters(), query);
  const from = (data.page - 1) * data.page_size + 1;
  const to = from + data.rows.length - 1;

  const rows = data.rows.map((row) => ({
    id: row.member_id,
    title: row.title || '–',
    member: row.name,
    unit: row.school ?? '–',
    orcid: row.orcid,
    orcidUrl: row.orcid_url,
    records: formatNumber(row.publications),
  }));

  return (
    <>
      <PageHeader title="Members" />

      <Card className="mb-24" aria-labelledby="view-title">
        <CardHeader
          id="view-title"
          title="Authorised member view"
          subtitle="Executive access · individuals are listed alphabetically, never ranked"
          className="mb-8"
        />
        <form className="toolbar" role="search" action="/members" method="get" aria-label="Filter members">
          <label className="sr-only" htmlFor="member-search">
            Search members
          </label>
          <input
            className="toolbar__search"
            id="member-search"
            type="search"
            name="q"
            defaultValue={query.q}
            placeholder="Search members…"
            autoComplete="off"
          />
          <div className="toolbar__filters">
            <SelectLink id="member-orcid" name="orcid" label="ORCID" options={ORCID_OPTIONS} defaultValue={query.orcid} />
            <SelectLink id="member-sort" name="sort" label="Sort" options={['Sort: A–Z']} />
          </div>
          <Button type="submit" variant="secondary" size="sm">
            Search
          </Button>
        </form>
      </Card>

      <Card aria-labelledby="directory-title">
        <CardHeader
          id="directory-title"
          title="Members directory"
          subtitle="Staff from the HR roster whose names match a publication author · the filters above choose who is listed and what is counted"
        />
        {!data.available ? (
          <p className="text-muted">
            The member directory needs the staff roster, which is not loaded in this environment.
          </p>
        ) : data.rows.length === 0 ? (
          <p className="text-muted">No members have publications that match these filters and this search.</p>
        ) : (
          <DataTable caption="Members listed alphabetically" columns={COLUMNS} rows={rows} variant="roomy" />
        )}
        <Pager
          label="Members pagination"
          summary={
            data.total
              ? `Showing ${formatNumber(from)}–${formatNumber(to)} of ${formatNumber(data.total)} members`
              : '0 members'
          }
          previous={data.page > 1 ? { label: '← Previous', href: memberPageHref(query, data.page - 1) } : undefined}
          pages={[{ label: String(data.page), href: memberPageHref(query, data.page), current: true }]}
          next={data.page < data.pages ? { label: 'Next →', href: memberPageHref(query, data.page + 1) } : undefined}
        />
      </Card>
    </>
  );
}
