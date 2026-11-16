import AppShell from '@/components/layout/AppShell';
import { readFilters } from '@/lib/filters-server';
import { formatRefreshed, loadShellData } from '@/lib/shell-data';

/**
 * Server wrapper for the app shell: loads the real filter options and the last
 * pipeline run, then hands them to the client-side shell.
 */
export default async function Shell({ children }) {
  const [{ options, lastRun }, initialFilters] = await Promise.all([loadShellData(), readFilters()]);

  return (
    <AppShell
      filterOptions={options}
      initialFilters={initialFilters}
      refreshed={formatRefreshed(lastRun) ?? 'Not yet recorded'}
    >
      {children}
    </AppShell>
  );
}
