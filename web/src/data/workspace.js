/** Mock content for reports, dashboards and notifications. */

export const reportFormats = [
  { value: 'pdf', title: 'PDF' },
  { value: 'pptx', title: 'PowerPoint' },
  { value: 'xlsx', title: 'Excel' },
];

export const recentReports = [
  { id: 1, report: 'Executive research overview', format: 'PDF', generated: '16 Nov 2026', generatedIso: '2026-11-16', status: 'Ready' },
  { id: 2, report: 'Unit comparison briefing', format: 'PPT', generated: '9 Nov 2026', generatedIso: '2026-11-09', status: 'Ready' },
  { id: 3, report: 'Publication register', format: 'Excel', generated: '9 Nov 2026', generatedIso: '2026-11-09', status: 'Ready' },
];

export const dashboards = [
  {
    id: 'exec',
    title: 'Executive overview',
    description: 'Organisation KPIs, trends and coverage',
    scope: 'Organisation-wide · Executive',
    href: '/overview',
  },
  {
    id: 'unit',
    title: 'My unit',
    description: 'Unit totals, distributions and sub-units',
    scope: 'Own unit only · Unit head',
    href: '/organisation/medicine',
  },
  {
    id: 'library',
    title: 'Library operations',
    description: 'Source health, data quality and deposits',
    scope: 'Research operations · Librarian',
    href: '/data-quality',
  },
];

/** `category` drives the filter tabs; `unread` the "Unread" tab. */
export const notifications = [
  { id: 1, category: 'source', title: 'Refresh complete', text: 'All 18 source connectors completed the weekly refresh.', time: '16 Nov · 06:14', iso: '2026-11-16T06:14', action: 'View sources →', href: '/data-sources' },
  { id: 2, category: 'reports', unread: true, title: 'Report ready', text: 'Executive research overview is ready to download.', time: '16 Nov · 08:03', iso: '2026-11-16T08:03', action: 'Download PDF →', href: '/reports' },
  { id: 3, category: 'corrections', title: 'Correction reviewed', text: 'Your record correction was approved by the data librarian.', time: '15 Nov · 14:26', iso: '2026-11-15T14:26', action: 'View record →', href: '/publications/example-record' },
  { id: 4, category: 'source', unread: true, title: 'Review requested', text: '67 flagged matches are waiting for a steward decision.', time: '14 Nov · 09:10', iso: '2026-11-14T09:10', action: 'Open queue →', href: '/data-quality' },
  { id: 5, category: 'invitations', unread: true, title: 'New workspace invitation', text: 'An Analyst invitation is awaiting acceptance.', time: '13 Nov · 11:32', iso: '2026-11-13T11:32', action: 'Manage users →', href: '/admin/users' },
];

export const notificationTabs = [
  { id: 'all', label: 'All' },
  { id: 'unread', label: 'Unread' },
  { id: 'source', label: 'Source alerts' },
  { id: 'reports', label: 'Reports' },
  { id: 'corrections', label: 'Corrections' },
];
