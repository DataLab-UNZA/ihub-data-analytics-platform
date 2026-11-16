/**
 * Primary navigation. The single place where sidebar items are defined.
 * `id` is referenced by `nav` in src/config/screens.js to mark the active item.
 */
export const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', href: '/overview' },
  { id: 'organisation', label: 'Organisation', href: '/organisation' },
  { id: 'compare', label: 'Compare units', href: '/compare-units' },
  { id: 'members', label: 'Members', href: '/members' },
  { id: 'publications', label: 'Publications', href: '/publications' },
  { id: 'journals', label: 'Journals', href: '/journals' },
  { id: 'topics', label: 'Topics', href: '/topics' },
  { id: 'collaboration', label: 'Collaboration', href: '/collaboration' },
  { id: 'coverage', label: 'Coverage', href: '/coverage' },
  { id: 'quality', label: 'Data quality', href: '/data-quality' },
  { id: 'sources', label: 'Data sources', href: '/data-sources' },
  { id: 'reports', label: 'Reports', href: '/reports' },
  { id: 'dashboards', label: 'Dashboards', href: '/dashboards' },
  { id: 'notifications', label: 'Notifications', href: '/notifications' },
  { id: 'admin', label: 'Admin', href: '/admin/hierarchy' },
];
