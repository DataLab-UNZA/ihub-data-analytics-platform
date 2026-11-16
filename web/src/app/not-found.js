import Link from 'next/link';
import Shell from '@/components/layout/Shell';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import StateCard from '@/components/ui/StateCard';

export const metadata = {
  title: 'Page not found',
  description: 'The requested page could not be found.',
};

/**
 * Global 404. It sits outside the (app) route group, so it wraps itself in
 * the shell to keep the sidebar and top bar visible.
 */
export default function NotFound() {
  return (
    <Shell>
      <PageHeader title="Page not found" />
      <StateCard id="state-title" title="This page couldn’t be found">
        <p className="state__code" aria-label="Error 404">
          404
        </p>
        <p className="state__title">The link may have moved.</p>
        <p className="state__text">
          Your workspace and data are still here. Search for a record, or return to your overview.
        </p>
        <div className="btn-row state__actions">
          <Button size="lg" href="/overview">
            Back to home
          </Button>
          <Button variant="secondary" size="md" href="/search">
            Search workspace
          </Button>
        </div>
        <p className="state__note">
          <Link href="/notifications">Need help? Contact your workspace admin.</Link>
        </p>
      </StateCard>
    </Shell>
  );
}
