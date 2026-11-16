'use client';

import { createContext, startTransition, useCallback, useContext, useMemo, useState, useSyncExternalStore } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { FILTER_DEFAULTS, withOptions } from '@/config/filters';
import { getScreen } from '@/config/screens';
import { getSnapshot, saveFilters, subscribe } from '@/lib/filter-store';

const FiltersContext = createContext(null);

/**
 * Holds the global filters shared by every signed-in screen.
 *
 * Precedence, lowest to highest: defaults, values saved in the filters cookie,
 * values a screen sets on load (see `filters` in config/screens.js), and
 * changes the user makes on the current screen. Changing a filter saves the
 * cookie and refreshes the route, so server components re-read the data.
 *
 * @param {object} initial Cookie values read on the server (avoids a flash on first paint).
 * @param {object} options Real option lists from the data service, keyed by filter.
 */
export function FiltersProvider({ initial = {}, options, children }) {
  const pathname = usePathname();
  const router = useRouter();
  const screenFilters = getScreen(pathname).filters;
  const stored = useSyncExternalStore(subscribe, getSnapshot, () => initial);
  const [changes, setChanges] = useState({ pathname, values: {} });
  const definitions = useMemo(() => withOptions(options), [options]);

  // Changes made on one screen do not leak into the screen-defined state of the next.
  const localChanges = changes.pathname === pathname ? changes.values : null;

  const values = useMemo(
    () => ({ ...FILTER_DEFAULTS, ...stored, ...screenFilters, ...localChanges }),
    [stored, screenFilters, localChanges],
  );

  const commit = useCallback(
    (next, changed) => {
      saveFilters(next);
      setChanges((current) => ({
        pathname,
        values: { ...(current.pathname === pathname ? current.values : {}), ...changed },
      }));
      startTransition(() => router.refresh());
    },
    [pathname, router],
  );

  const setFilter = useCallback(
    (key, value) => commit({ ...getSnapshot(), [key]: value }, { [key]: value }),
    [commit],
  );

  const resetFilters = useCallback(
    (key) => {
      if (key) {
        setFilter(key, FILTER_DEFAULTS[key]);
        return;
      }
      commit({}, { ...FILTER_DEFAULTS });
    },
    [commit, setFilter],
  );

  const value = useMemo(
    () => ({ values, definitions, setFilter, resetFilters }),
    [values, definitions, setFilter, resetFilters],
  );

  return <FiltersContext.Provider value={value}>{children}</FiltersContext.Provider>;
}

export function useFilters() {
  const context = useContext(FiltersContext);
  if (!context) {
    throw new Error('useFilters must be used inside <FiltersProvider>.');
  }
  return context;
}
