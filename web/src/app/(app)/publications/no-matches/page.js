import ActiveFilterChips from '@/components/features/publications/ActiveFilterChips';
import ClearFiltersButton from '@/components/features/publications/ClearFiltersButton';
import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import StateCard from '@/components/ui/StateCard';

export const metadata = {
  title: 'Publications (no matches)',
  description: 'Empty state shown when no publications match the current global filters.',
};

export default function NoMatchesPage() {
  return (
    <>
      <PageHeader title="Publications" />
      <StateCard
        id="empty-title"
        title="No publications match these filters"
        subtitle="Your sources are connected. This combination of filters returned no records."
        short
      >
        <p className="state__title">Try a broader view</p>
        <p className="state__text">
          Remove a source or type filter, choose another period, or search using a different phrase.
        </p>
        <ActiveFilterChips />
        <div className="btn-row state__actions">
          <ClearFiltersButton size="lg" />
          <Button variant="secondary" size="md" href="/publications">
            Search all publications
          </Button>
        </div>
        <p className="state__note">No results is different from missing data. Missing values are labelled Unknown.</p>
      </StateCard>
    </>
  );
}
