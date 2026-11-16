import BrandingEditor from '@/components/features/admin/BrandingEditor';
import PageHeader from '@/components/layout/PageHeader';

export const metadata = {
  title: 'Branding',
  description: 'Set the workspace display name, wordmark and accent colour with contrast protection.',
};

export default function BrandingPage() {
  return (
    <>
      <PageHeader title="Branding" />
      <BrandingEditor />
    </>
  );
}
