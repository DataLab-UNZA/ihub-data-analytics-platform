import BoxPlot from '@/components/charts/BoxPlot';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import Chip from '@/components/ui/Chip';
import DataTable from '@/components/ui/DataTable';
import Grid from '@/components/ui/Grid';
import { comparedUnits, comparisonRows, staffDistribution } from '@/data/organisation';

export const metadata = {
  title: 'Compare units',
  description: 'Compare two to six units using totals, per-staff and per-FTE output measures.',
};

const COLUMNS = [
  { key: 'unit', header: 'Unit', rowHeader: true, href: () => '/organisation/medicine' },
  { key: 'outputs', header: 'Outputs' },
  { key: 'staff', header: 'Staff' },
  { key: 'perStaff', header: 'Per staff' },
  { key: 'fte', header: 'FTE' },
  { key: 'perFte', header: 'Per FTE' },
];

export default function CompareUnitsPage() {
  return (
    <>
      <PageHeader title="Compare units" aside="Illustrative data · not connected yet" />

      <Card className="mb-24" aria-labelledby="choose-title">
        <h2 className="card__title" id="choose-title">
          Choose 2–6 units
        </h2>
        <ul className="chip-list mt-12" aria-label="Selected units">
          {comparedUnits.map((unit) => (
            <li key={unit}>
              <Chip>{unit}</Chip>
            </li>
          ))}
          <li>
            <button className="chip" type="button">
              + Add unit
            </button>
          </li>
        </ul>
      </Card>

      <Card className="mb-24" aria-labelledby="fair-title">
        <CardHeader
          id="fair-title"
          title="A fair view of unit output"
          subtitle="Illustrative manual baselines · organisation-wide staff coverage remains incomplete"
        />
        <DataTable
          caption="Output, staff and FTE measures for the selected units"
          columns={COLUMNS}
          rows={comparisonRows}
          variant="measures"
        />
      </Card>

      <Grid variant="main-aside">
        <Card aria-labelledby="dist-title">
          <CardHeader
            id="dist-title"
            title="Staff output distribution"
            subtitle="Box plot · median, interquartile range and full range · no individual names"
          />
          <BoxPlot
            title="Distribution of outputs per staff member by unit"
            description="Box plot showing the median, interquartile range and full range for Agricultural Sciences, Education and Medicine. The same values are listed in the table below."
            tableCaption="Outputs per staff member: five-number summary by unit (illustrative)"
            rows={staffDistribution}
          />
        </Card>

        <Card aria-labelledby="read-title">
          <CardHeader id="read-title" title="Read comparisons responsibly" />
          <h3>Different units, different contexts</h3>
          <p className="text-muted mt-20">
            Use totals alongside per-staff and per-FTE figures. Distributions include staff with zero recorded outputs.
          </p>
          <h3 className="text-link mt-40">Unknown ≠ zero</h3>
          <p className="text-muted mt-16 text-sm">Missing denominators are excluded, never estimated.</p>
        </Card>
      </Grid>
    </>
  );
}
