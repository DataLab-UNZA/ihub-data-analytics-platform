import Image from 'next/image';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import { dashboards } from '@/data/workspace';

export const metadata = {
  title: 'Dashboards',
  description: 'Curated dashboards for executives, unit heads and library operations.',
};

export default function DashboardsPage() {
  return (
    <>
      <PageHeader title="Dashboards" aside="Illustrative data · not connected yet" />

      <Card className="mb-24" aria-labelledby="your-title">
        <div className="card__head--split card__head--end">
          <div>
            <h2 className="card__title" id="your-title">
              Your dashboards
            </h2>
            <p className="card__sub">Curated views · every dashboard carries the same global filters</p>
          </div>
          <Button size="md">Create dashboard</Button>
        </div>
      </Card>

      <Grid variant="thirds">
        {dashboards.map((dashboard) => (
          <Card as="article" className="dash-card" aria-labelledby={`dash-${dashboard.id}`} key={dashboard.id}>
            <header>
              <h2 className="card__title" id={`dash-${dashboard.id}`}>
                {dashboard.title}
              </h2>
              <p className="card__sub">{dashboard.description}</p>
            </header>
            <Image className="thumb" src="/img/dashboard-thumb.svg" alt="" width={322} height={186} unoptimized />
            <p className="dash-card__scope">{dashboard.scope}</p>
            <Button variant="secondary" href={dashboard.href} block>
              Open dashboard<span className="sr-only">: {dashboard.title}</span>
            </Button>
          </Card>
        ))}
      </Grid>

      <Card aria-labelledby="defs-title">
        <h2 className="card__title" id="defs-title">
          Shared definitions
        </h2>
        <p className="text-muted mt-32 text-md">
          A dashboard changes the view, not the evidence. Every metric links back to the same reconciled source
          records.
        </p>
      </Card>
    </>
  );
}
