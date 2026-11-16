import Button from '@/components/ui/Button';
import StateCard from '@/components/ui/StateCard';
import PageHeader from '@/components/layout/PageHeader';

/**
 * Error state for the overview. Used by the route's error boundary (error.js)
 * and by the preview route.
 *
 * @param {() => void} onRetry Optional retry handler; falls back to a link to the overview.
 */
export default function OverviewError({ onRetry }) {
  return (
    <>
      <PageHeader title="Your organisation, at a glance" />
      <StateCard
        id="error-title"
        title="We couldn’t load this snapshot"
        subtitle="Your data and saved filters have not changed."
        short
        role="alert"
      >
        <p className="state__title">Let’s try that again.</p>
        <p className="state__text">
          A temporary connection problem prevented this dashboard from loading. Retry, or check source status.
        </p>
        <div className="btn-row state__actions">
          {onRetry ? (
            <Button size="lg" onClick={onRetry}>
              Try again
            </Button>
          ) : (
            <Button size="lg" href="/overview">
              Try again
            </Button>
          )}
          <Button variant="secondary" size="md" href="/data-sources">
            View source status
          </Button>
        </div>
        <h3 className="state__subhead">Still having trouble?</h3>
        <p className="state__text text-md mt-20">
          Contact your workspace admin and include reference IHUB-LOAD-01. No metric is shown as zero when loading
          fails.
        </p>
      </StateCard>
    </>
  );
}
