import OverviewLoading from '@/components/features/overview/OverviewLoading';

export const metadata = {
  title: 'Loading overview',
  description: 'Loading state for the executive overview while global filters are applied.',
};

/** Design preview of the loading state (the live one is loading.js). */
export default function LoadingPreviewPage() {
  return <OverviewLoading />;
}
