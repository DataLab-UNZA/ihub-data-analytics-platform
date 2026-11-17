import AppShell from '@/components/layout/AppShell';
import { currentUser } from '@/lib/api';
import { readFilters } from '@/lib/filters-server';
import { formatRefreshed, loadShellData } from '@/lib/shell-data';

/**
 * Server wrapper for the app shell: loads the real filter options, the last pipeline run
 * and the signed-in user (null when sign-in is off), then hands them to the client shell.
 */
export default async function Shell({ children }) {
  const [{ options, lastRun }, initialFilters, user] = await Promise.all([
    loadShellData(),
    readFilters(),
    currentUser(),
  ]);

  return (
    <AppShell
      filterOptions={options}
      initialFilters={initialFilters}
      user={user}
      refreshed={formatRefreshed(lastRun) ?? 'Not yet recorded'}
    >
      {children}
    </AppShell>
  );
}
