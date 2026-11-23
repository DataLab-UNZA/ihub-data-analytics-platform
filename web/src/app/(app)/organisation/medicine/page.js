import LineChart from '@/components/charts/LineChart';
import PageHeader from '@/components/layout/PageHeader';
import BarList from '@/components/ui/BarList';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import KpiGrid from '@/components/ui/Kpi';
import {
  medicineJournals,
  medicineKpis,
  medicineMembers,
  medicineSeries,
  medicineSubunits,
} from '@/data/organisation';

export const metadata = {
  title: 'School of Medicine',
  description: 'Research output, sub-units, journals and members for the School of Medicine.',
};

const JOURNAL_COLUMNS = [
  { key: 'journal', header: 'Journal', rowHeader: true, href: () => '/journals' },
  { key: 'outputs', header: 'Outputs' },
];

const MEMBER_COLUMNS = [
  { key: 'member', header: 'Member', rowHeader: true, href: () => '/members' },
  { key: 'unit', header: 'Unit' },
  { key: 'orcid', header: 'ORCID' },
];

export default function MedicineUnitPage() {
  return (
    <>
      <PageHeader title="School of Medicine" aside="Illustrative data · not connected yet" />
      <KpiGrid items={medicineKpis} />

      <Grid variant="main-aside">
        <Card aria-labelledby="trend-title">
          <CardHeader id="trend-title" title="Output trend" subtitle="Medicine · all sub-units included" />
          <LineChart
            id="medicine-output"
            caption="School of Medicine output per year, 2015 to 2026"
            data={medicineSeries}
            drillHref="/publications"
          />
        </Card>
        <Card aria-labelledby="subunits-title">
          <CardHeader id="subunits-title" title="Sub-units" subtitle="Department totals · select to explore" />
          <BarList items={medicineSubunits} max={2740} />
        </Card>
      </Grid>

      <Grid variant="halves">
        <Card aria-labelledby="unit-journals-title">
          <CardHeader id="unit-journals-title" title="Journals" subtitle="Outputs linked to this unit" />
          <DataTable
            caption="Journals with outputs linked to the School of Medicine"
            columns={JOURNAL_COLUMNS}
            rows={medicineJournals}
          />
        </Card>
        <Card aria-labelledby="unit-members-title">
          <CardHeader id="unit-members-title" title="Members · A–Z" subtitle="Authorised view · no rankings" />
          <DataTable
            caption="Members of the School of Medicine, listed alphabetically"
            columns={MEMBER_COLUMNS}
            rows={medicineMembers}
          />
        </Card>
      </Grid>
    </>
  );
}
