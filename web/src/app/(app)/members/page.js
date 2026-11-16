import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { SelectLink } from '@/components/ui/Form';
import Pager from '@/components/ui/Pager';
import { memberDirectory, memberUnits } from '@/data/members';

export const metadata = {
  title: 'Members',
  description: 'Authorised, alphabetical member directory. Individuals are never ranked.',
};

const PROFILE = '/members/chanda-banda';

const COLUMNS = [
  { key: 'member', header: 'Member A–Z', rowHeader: true, href: () => PROFILE },
  { key: 'unit', header: 'Unit' },
  { key: 'orcid', header: 'ORCID' },
  { key: 'records', header: 'Records' },
  { key: 'access', header: 'Access', render: () => <Link href={PROFILE}>View profile →</Link> },
];

export default function MembersPage() {
  return (
    <>
      <PageHeader title="Members" aside="Illustrative data · not connected yet" />

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
            placeholder="Search members…"
            autoComplete="off"
          />
          <div className="toolbar__filters">
            <SelectLink id="member-unit" name="unit" label="Unit" options={memberUnits} />
            <SelectLink id="member-orcid" name="orcid" label="ORCID" options={['ORCID: All', 'Linked', 'Unknown']} />
            <SelectLink id="member-sort" name="sort" label="Sort" options={['Sort: A–Z']} />
          </div>
        </form>
      </Card>

      <Card aria-labelledby="directory-title">
        <CardHeader
          id="directory-title"
          title="Members directory"
          subtitle="Names and affiliations are illustrative • member-level information is role restricted"
        />
        <DataTable caption="Members listed alphabetically" columns={COLUMNS} rows={memberDirectory} variant="roomy" />
        <Pager
          label="Members pagination"
          summary="Showing 1–6 of 6 preview members"
          href="/members"
          previous="Previous"
          pages={[{ label: '1', current: true }]}
          next="Next"
        />
      </Card>
    </>
  );
}
