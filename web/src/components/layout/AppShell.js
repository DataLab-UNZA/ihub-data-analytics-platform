'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { FiltersProvider } from '@/context/filters-context';
import { getScreen } from '@/config/screens';
import { cx } from '@/lib/format';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import SiteFooter from './SiteFooter';

/**
 * Frame for every signed-in screen: sidebar, top bar, content and footer.
 * The active navigation item and role come from the screen registry, so pages
 * only render their own content. Use <Shell> from a server component; it loads
 * the props below.
 *
 * @param {string} refreshed Text shown under "Weekly refresh" in the sidebar.
 * @param {object} filterOptions Real option lists for the global filters.
 * @param {object} initialFilters Filter values saved in the browser's cookie.
 */
export default function AppShell({ children, refreshed, filterOptions, initialFilters }) {
  const pathname = usePathname();
  const screen = getScreen(pathname);
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <FiltersProvider initial={initialFilters} options={filterOptions}>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <div className={cx('app', menuOpen && 'app--menu-open')}>
        <Sidebar active={screen.nav} role={screen.role} refreshed={refreshed ?? screen.refreshed} />
        <div className="app__body">
          <Topbar role={screen.role} menuOpen={menuOpen} onToggleMenu={() => setMenuOpen((open) => !open)} />
          <main className="main" id="main">
            {children}
          </main>
          <SiteFooter />
        </div>
      </div>
    </FiltersProvider>
  );
}
