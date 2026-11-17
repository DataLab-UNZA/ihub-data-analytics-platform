/**
 * Primary navigation: the top menu, in the style of Apache Superset's header.
 * `id` is referenced by `nav` in src/config/screens.js to mark the active item.
 * `permission` hides an item from users whose role lacks it (ADR-010; the API enforces
 * the same rule, this only keeps the menu honest). A group with no visible child is hidden.
 */
export const NAV_ITEMS = [
  { id: 'dashboards', label: 'Dashboards', href: '/dashboards' },
  { id: 'charts', label: 'Charts', href: '/charts' },
  { id: 'explore', label: 'Explore', href: '/explore' },
  {
    id: 'research',
    label: 'Research',
    children: [
      { id: 'overview', label: 'Overview', href: '/overview' },
      { id: 'publications', label: 'Publications', href: '/publications' },
      { id: 'journals', label: 'Journals', href: '/journals' },
      { id: 'topics', label: 'Topics', href: '/topics' },
      { id: 'collaboration', label: 'Collaboration', href: '/collaboration' },
      { id: 'coverage', label: 'Source coverage', href: '/coverage' },
    ],
  },
  {
    id: 'people',
    label: 'Organisation',
    children: [
      { id: 'organisation', label: 'Schools and units', href: '/organisation' },
      { id: 'compare', label: 'Compare units', href: '/compare-units' },
      { id: 'members', label: 'Members', href: '/members' },
    ],
  },
  {
    id: 'data',
    label: 'Data',
    children: [
      { id: 'sources', label: 'Data sources', href: '/data-sources', permission: 'sources:manage' },
      { id: 'quality', label: 'Data quality', href: '/data-quality', permission: 'quality:review' },
      { id: 'reports', label: 'Reports', href: '/reports', permission: 'reports:manage' },
    ],
  },
  {
    id: 'settings',
    label: 'Settings',
    children: [
      { id: 'admin', label: 'Users & roles', href: '/admin/users', permission: 'users:manage' },
      { id: 'hierarchy', label: 'Hierarchy & labels', href: '/admin/hierarchy', permission: 'users:manage' },
      { id: 'modules', label: 'Modules', href: '/admin/modules', permission: 'users:manage' },
      { id: 'branding', label: 'Branding', href: '/admin/branding', permission: 'users:manage' },
      { id: 'notifications', label: 'Notifications', href: '/notifications', permission: 'users:manage' },
    ],
  },
];

/** The ids of an item and its group, for highlighting the menu. */
export function activePath(id) {
  for (const item of NAV_ITEMS) {
    if (item.id === id) return [item.id];
    if (item.children?.some((child) => child.id === id)) return [item.id, id];
  }
  return [];
}
