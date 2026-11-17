'use client';

import { usePathname } from 'next/navigation';
import { FiltersProvider } from '@/context/filters-context';
import { getScreen } from '@/config/screens';
import Header from './Header';
import SiteFooter from './SiteFooter';

/**
 * Frame for every signed-in screen, laid out like Apache Superset: a top header with the
 * main menu, and the page below it. Only the page panel scrolls (scrollbar hidden).
 * Use <Shell> from a server component; it loads the props below.
 *
 * @param {string} refreshed Text for "Data refreshed …" in the header.
 * @param {object} filterOptions Real option lists for the global filters.
 * @param {object} initialFilters Filter values saved in the browser's cookie.
 * @param {object|null} user The signed-in user from /api/auth/me (null when sign-in is off).
 */
export default function AppShell({ children, refreshed, filterOptions, initialFilters, user }) {
  const pathname = usePathname();
  const screen = getScreen(pathname);

  return (
    <FiltersProvider initial={initialFilters} options={filterOptions}>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <div className="app">
        <Header active={screen.nav} user={user} refreshed={refreshed ?? screen.refreshed} />
        <div className="app__body">
          <main className="main" id="main">
            {children}
          </main>
          <SiteFooter />
        </div>
      </div>
    </FiltersProvider>
  );
}
