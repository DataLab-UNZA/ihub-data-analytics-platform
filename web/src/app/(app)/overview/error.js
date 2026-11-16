'use client';

import OverviewError from '@/components/features/overview/OverviewError';

/** Error boundary for the overview segment. `reset` re-renders the segment. */
export default function Error({ reset }) {
  return <OverviewError onRetry={reset} />;
}
