/**
 * Screen registry: the single source of truth for every route.
 *
 *   n          position in the supplied design set (used by the screen index)
 *   group      section heading on the screen index
 *   title      label on the screen index
 *   path       URL path
 *   nav        active sidebar item (signed-in screens only)
 *   role       role shown in the top bar and sidebar (default: executive)
 *   refreshed  text under "Weekly refresh" in the sidebar
 *   filters    global-filter values that this screen sets on load
 *
 * Document titles and descriptions live next to each page as `metadata`.
 */
export const DEFAULT_REFRESHED = '16 Nov 2026 · 06:00 CAT';

export const SCREEN_GROUPS = [
  'Authentication',
  'Overview',
  'Organisation and people',
  'Publications and research',
  'Data operations',
  'Workspace and admin',
  'System states and design',
];

export const SCREENS = [
  // Authentication
  { n: 9, group: 'Authentication', title: 'Sign in', path: '/login' },
  { n: 10, group: 'Authentication', title: 'Sign in · error', path: '/login/error' },
  { n: 11, group: 'Authentication', title: 'Forgot password', path: '/forgot-password' },
  { n: 12, group: 'Authentication', title: 'Create a password', path: '/create-password' },
  { n: 13, group: 'Authentication', title: 'Check your email · code', path: '/verify-code' },
  { n: 14, group: 'Authentication', title: 'Join your organisation', path: '/accept-invitation' },
  { n: 15, group: 'Authentication', title: 'Choose a workspace', path: '/choose-workspace' },
  { n: 16, group: 'Authentication', title: 'Session expired', path: '/login/session-expired' },
  { n: 17, group: 'Authentication', title: 'Check your inbox', path: '/forgot-password/sent' },

  // Overview
  { n: 18, group: 'Overview', title: 'Overview', path: '/overview', nav: 'overview' },
  {
    n: 4, group: 'Overview', title: 'Overview · stale data', path: '/overview/stale', nav: 'overview',
  },
  { n: 5, group: 'Overview', title: 'Overview · loading', path: '/overview/loading-preview', nav: 'overview' },
  { n: 7, group: 'Overview', title: 'Overview · error', path: '/overview/error-preview', nav: 'overview' },

  // Organisation and people
  { n: 19, group: 'Organisation and people', title: 'Organisation', path: '/organisation', nav: 'organisation' },
  {
    n: 20, group: 'Organisation and people', title: 'School of Medicine', path: '/organisation/medicine',
    nav: 'organisation', filters: { unit: 'medicine' },
  },
  { n: 21, group: 'Organisation and people', title: 'Compare units', path: '/compare-units', nav: 'compare' },
  { n: 22, group: 'Organisation and people', title: 'Members', path: '/members', nav: 'members' },
  { n: 23, group: 'Organisation and people', title: 'Member profile', path: '/members/chanda-banda', nav: 'members' },

  // Publications and research
  { n: 24, group: 'Publications and research', title: 'Publications', path: '/publications', nav: 'publications' },
  {
    n: 25, group: 'Publications and research', title: 'Publication record', path: '/publications/example-record',
    nav: 'publications',
  },
  {
    n: 6, group: 'Publications and research', title: 'Publications · no matches', path: '/publications/no-matches',
    nav: 'publications', filters: { period: '2026', unit: 'medicine', source: 'repository', type: 'chapter' },
  },
  { n: 1, group: 'Publications and research', title: 'Search results', path: '/search', nav: 'overview' },
  { n: 26, group: 'Publications and research', title: 'Journals', path: '/journals', nav: 'journals' },
  { n: 27, group: 'Publications and research', title: 'Topics', path: '/topics', nav: 'topics' },
  { n: 28, group: 'Publications and research', title: 'Collaboration', path: '/collaboration', nav: 'collaboration' },
  { n: 29, group: 'Publications and research', title: 'Source coverage', path: '/coverage', nav: 'coverage' },

  // Data operations
  { n: 30, group: 'Data operations', title: 'Data quality', path: '/data-quality', nav: 'quality', role: 'librarian' },
  { n: 31, group: 'Data operations', title: 'Data sources', path: '/data-sources', nav: 'sources', role: 'admin' },
  {
    n: 32, group: 'Data operations', title: 'Add source · 1 Choose', path: '/data-sources/add/choose',
    nav: 'sources', role: 'admin',
  },
  {
    n: 33, group: 'Data operations', title: 'Add source · 2 Connect', path: '/data-sources/add/connect',
    nav: 'sources', role: 'admin',
  },
  {
    n: 34, group: 'Data operations', title: 'Add source · 3 Map fields', path: '/data-sources/add/map-fields',
    nav: 'sources', role: 'admin',
  },
  {
    n: 35, group: 'Data operations', title: 'Add source · 4 Review', path: '/data-sources/add/review',
    nav: 'sources', role: 'admin',
  },
  {
    n: 36, group: 'Data operations', title: 'Repository connection failed', path: '/data-sources/repository',
    nav: 'sources', role: 'admin',
  },

  // Workspace and admin
  { n: 37, group: 'Workspace and admin', title: 'Reports', path: '/reports', nav: 'reports' },
  { n: 38, group: 'Workspace and admin', title: 'Dashboards', path: '/dashboards', nav: 'dashboards' },
  {
    n: 39, group: 'Workspace and admin', title: 'Notifications', path: '/notifications',
    nav: 'notifications', role: 'admin',
  },
  { n: 40, group: 'Workspace and admin', title: 'Hierarchy & labels', path: '/admin/hierarchy', nav: 'admin', role: 'admin' },
  { n: 41, group: 'Workspace and admin', title: 'Users & roles', path: '/admin/users', nav: 'admin', role: 'admin' },
  { n: 42, group: 'Workspace and admin', title: 'Modules', path: '/admin/modules', nav: 'admin', role: 'admin' },
  { n: 43, group: 'Workspace and admin', title: 'Branding', path: '/admin/branding', nav: 'admin', role: 'admin' },

  // System states and design
  { n: 2, group: 'System states and design', title: '404 · Page not found', path: '/missing-page', nav: 'overview' },
  {
    n: 3, group: 'System states and design', title: '403 · Access restricted', path: '/access-restricted',
    nav: 'overview', role: 'member',
  },
  { n: 8, group: 'System states and design', title: 'Foundations', path: '/foundations' },
];

const NO_FILTERS = Object.freeze({});
const FALLBACK = { nav: 'overview', role: 'executive' };

/**
 * Metadata for the shell, looked up by pathname: an exact match first, then the longest
 * registered path the pathname sits under (so /publications/<key> inherits /publications).
 * Unknown paths (404) fall back to the overview shell.
 */
export function getScreen(pathname) {
  const clean = pathname.length > 1 ? pathname.replace(/\/$/, '') : pathname;
  const screen =
    SCREENS.find((item) => item.path === clean) ??
    SCREENS.filter((item) => item.path !== '/' && clean.startsWith(`${item.path}/`)).sort(
      (a, b) => b.path.length - a.path.length,
    )[0];
  return {
    ...FALLBACK,
    refreshed: DEFAULT_REFRESHED,
    filters: NO_FILTERS,
    ...(screen ?? {}),
  };
}

export function screensInGroup(group) {
  return SCREENS.filter((screen) => screen.group === group);
}
