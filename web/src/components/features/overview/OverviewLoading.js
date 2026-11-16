import Card, { CardHeader } from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import PageHeader from '@/components/layout/PageHeader';
import { loadingBarHeights, loadingKpiTitles } from '@/data/overview';

/** Skeleton shown while the overview snapshot loads. Used by loading.js and the preview route. */
export default function OverviewLoading() {
  return (
    <>
      <PageHeader title="Loading your overview" />

      <Grid as="section" variant="kpi" aria-label="Key figures loading">
        {loadingKpiTitles.map((title) => (
          <Card as="article" className="kpi kpi--titled" key={title}>
            <h2 className="kpi__label">{title}</h2>
            <p className="kpi__value">
              <span className="skeleton" aria-hidden="true" />
            </p>
            <p className="kpi__note" role="status">
              Loading…
            </p>
          </Card>
        ))}
      </Grid>

      <Card aria-labelledby="snapshot-title" aria-busy="true">
        <CardHeader
          id="snapshot-title"
          title="Loading weekly snapshot"
          subtitle="Your global filters are being applied. There are no results to interpret yet."
        />
        <div className="skeleton-chart" aria-hidden="true">
          {loadingBarHeights.map((height) => (
            <span key={height} style={{ '--h': height }} />
          ))}
        </div>
        <div className="stack stack--md mt-48">
          <p className="text-muted" role="status">
            Loading accessible summary…
          </p>
          <p className="text-muted">This normally takes a few seconds.</p>
        </div>
      </Card>
    </>
  );
}
