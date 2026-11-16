import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import StateCard from '@/components/ui/StateCard';

export const metadata = {
  title: 'Access restricted',
  description: 'The signed-in role does not have access to this view.',
};

export default function AccessRestrictedPage() {
  return (
    <>
      <PageHeader title="Access restricted" />
      <StateCard id="state-title" title="You don’t have access to this view">
        <p className="state__code" aria-label="Error 403">
          403
        </p>
        <p className="state__title">Your role protects sensitive information.</p>
        <p className="state__text">
          Member-level records and workspace administration are limited to authorised roles. No restricted data has
          been shown.
        </p>
        <div className="btn-row state__actions">
          <Button size="lg" href="/overview">
            Return to my workspace
          </Button>
          <Button variant="secondary" size="md" href="/notifications">
            Request access
          </Button>
        </div>
        <p className="state__note">Current role: Member · scope: own profile</p>
      </StateCard>
    </>
  );
}
