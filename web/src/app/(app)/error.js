'use client';

import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import StateCard from '@/components/ui/StateCard';

/**
 * Error boundary for every signed-in screen that has no error.js of its own.
 * It appears when the data service is down or returns an error.
 */
export default function AppError({ error, reset }) {
  return (
    <>
      <PageHeader title="Data unavailable" />
      <StateCard
        id="error-title"
        title="We couldn’t load this data"
        subtitle="Nothing has been changed. The numbers on this screen come from the research data service."
        short
        role="alert"
      >
        <p className="state__title">Let’s try that again.</p>
        <p className="state__text">
          The data service did not answer as expected. Retry, or check that it is running.
        </p>
        <div className="btn-row state__actions">
          <Button size="lg" onClick={reset}>
            Try again
          </Button>
          <Button variant="secondary" size="md" href="/data-sources">
            View source status
          </Button>
        </div>
        <p className="state__note">{error?.message ? `Details: ${error.message}` : null}</p>
      </StateCard>
    </>
  );
}
