import OverviewError from '@/components/features/overview/OverviewError';

export const metadata = {
  title: 'Snapshot could not load',
  description: 'Error state shown when the overview snapshot fails to load.',
};

/** Design preview of the error state (the live one is error.js). */
export default function ErrorPreviewPage() {
  return <OverviewError />;
}
