/** Mock content for administration screens. */

export const workspaceUsers = [
  { id: 1, user: 'Workspace admin', role: 'Admin', scope: 'Organisation', status: 'Active' },
  { id: 2, user: 'Research office', role: 'Executive', scope: 'All units', status: 'Active' },
  { id: 3, user: 'Medicine head', role: 'Unit head', scope: 'Medicine only', status: 'Active' },
];

export const rolePermissions = [
  { id: 'executive', role: 'Executive', scope: 'All units', individual: 'Authorised views', manage: 'No source edits' },
  { id: 'unit-head', role: 'Unit head', scope: 'Own unit + sub-units', individual: 'Own unit, if authorised', manage: 'No role edits' },
  { id: 'analyst', role: 'Analyst', scope: 'Assigned scope', individual: 'Only if granted', manage: 'Saved views & reports' },
  { id: 'librarian', role: 'Librarian', scope: 'Research records', individual: 'Record correction scope', manage: 'Quality & coverage' },
  { id: 'member', role: 'Member', scope: 'Own profile', individual: 'Self only', manage: 'Submit corrections' },
  { id: 'admin', role: 'Admin', scope: 'Configured scope', individual: 'Only if granted', manage: 'Users, sources, labels' },
];

export const modules = [
  {
    id: 'research',
    title: 'Research',
    state: 'Enabled',
    body: 'Publications, journals, collaborations, coverage and source reconciliation.',
    foot: 'Connected to 18 source connectors',
    footHref: '/data-sources',
    action: 'Open module',
    href: '/overview',
  },
  {
    id: 'teaching',
    title: 'Teaching',
    state: 'Coming soon',
    body: 'A future view of teaching activity. No data is collected by this module yet.',
    foot: 'Not available in this pilot',
    action: 'Coming soon',
  },
  {
    id: 'hr',
    title: 'HR',
    state: 'Coming soon',
    body: 'Staff and FTE denominators will be provided here when the module is available.',
    foot: 'Not available in this pilot',
    action: 'Coming soon',
  },
];

/** Editable level labels. `preview` is the unit name shown in the live preview. */
export const hierarchyFields = [
  { key: 'organisation', label: 'Organisation label', id: 'label-org', defaultValue: 'Organisation' },
  { key: 'level1', label: 'Level 1 unit label', id: 'label-l1', defaultValue: 'School' },
  { key: 'level2', label: 'Level 2 unit label', id: 'label-l2', defaultValue: 'Department' },
  { key: 'individual', label: 'Individual label', id: 'label-member', defaultValue: 'Member' },
];

export const brandingDefaults = {
  displayName: 'University of Zambia',
  productName: 'iHub Analytics',
  accent: '#27bedb',
};

export const brandingPreviewBars = ['32%', '46%', '38%', '66%', '82%', '90%', '100%'];
