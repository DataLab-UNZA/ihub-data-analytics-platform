/** Mock content for data-quality, data-source and add-source screens. */

export const qualityKpis = [
  { label: 'Unassigned outputs', value: '418', note: 'Missing organisational unit' },
  { label: 'Flagged matches', value: '67', note: 'Awaiting steward review' },
  { label: 'Possible duplicates', value: '124', note: 'Approve or split records' },
  { label: 'Staff completeness', value: 'Unknown', note: 'HR source not connected' },
];

export const reviewQueue = [
  { id: 1, item: 'Community health systems…', issue: 'Author match', action: 'Review →' },
  { id: 2, item: 'Digital learning in higher education', issue: 'No unit', action: 'Assign unit →' },
  { id: 3, item: 'Biodiversity across the Zambezi…', issue: 'Possible duplicate', action: 'Compare →' },
  { id: 4, item: 'Health workforce and service…', issue: 'Year mismatch', action: 'Review →' },
  { id: 5, item: 'Climate resilience…', issue: 'Source conflict', action: 'Review →' },
];

export const sourceHealth = [
  { id: 'openalex', source: 'OpenAlex', status: 'Healthy', lastRun: '16 Nov · 06:00', lastRunIso: '2026-11-16T06:00', received: '25,840', expected: '25,840' },
  { id: 'orcid', source: 'ORCID', status: 'Healthy', lastRun: '16 Nov · 06:04', lastRunIso: '2026-11-16T06:04', received: '18,920', expected: '18,920' },
  { id: 'repository', source: 'Repository', status: 'Healthy', lastRun: '16 Nov · 06:08', lastRunIso: '2026-11-16T06:08', received: '14,620', expected: '14,620' },
  { id: 'journals', source: '15 journals', status: 'Healthy', lastRun: '16 Nov · 06:12', lastRunIso: '2026-11-16T06:12', received: '7,500', expected: '7,500' },
];

export const ADD_SOURCE_STEPS = [
  { label: 'Choose source', href: '/data-sources/add/choose' },
  { label: 'Connect', href: '/data-sources/add/connect' },
  { label: 'Map fields', href: '/data-sources/add/map-fields' },
  { label: 'Review', href: '/data-sources/add/review' },
];

export const sourceTypes = [
  { value: 'openalex', title: 'OpenAlex', description: 'Organisation-linked research outputs' },
  { value: 'orcid', title: 'ORCID', description: 'Author identity and works' },
  { value: 'repository', title: 'Repository', description: 'OAI-PMH institutional repository' },
  { value: 'journal-feed', title: 'Journal feed', description: 'OAI-PMH or structured journal export' },
  { value: 'csv', title: 'CSV / Excel', description: 'Preview, map and validate an upload' },
];

export const authenticationOptions = ['None', 'API key', 'Username and password'];

export const fieldMappings = [
  { id: 'title', sourceField: 'dc.title', ihubField: 'Title', required: true, example: 'Community health systems…', validation: 'Valid' },
  { id: 'year', sourceField: 'dc.date.issued', ihubField: 'Publication year', required: true, example: '2026', validation: 'Valid' },
  { id: 'author', sourceField: 'dc.creator', ihubField: 'Author', example: 'C. Banda', validation: 'Review identity' },
  { id: 'identifier', sourceField: 'dc.identifier', ihubField: 'DOI / source identifier', required: true, example: 'repo:14620', validation: 'Valid' },
  { id: 'unit', sourceField: 'dc.relation', ihubField: 'Unit', example: 'Unknown', validation: 'Assign later' },
];

export const reviewSettings = [
  { id: 'connector', setting: 'Connector', href: '/data-sources/add/choose', value: 'OAI-PMH repository' },
  { id: 'expected', setting: 'Expected records', href: '/data-sources/add/connect', value: '14,620' },
  { id: 'schedule', setting: 'Refresh schedule', href: '/data-sources', value: 'Weekly · Monday · 06:00 CAT' },
  { id: 'owner', setting: 'Alert owner', href: '/notifications', value: 'Workspace admin' },
  { id: 'mapping', setting: 'Field mapping', href: '/data-sources/add/map-fields', value: '5 mapped · 1 review warning' },
];

export const failureDetails = [
  { id: 'status', detail: 'Status', value: 'Failed · authentication rejected' },
  { id: 'last', detail: 'Last successful run', value: '9 Nov 2026 · 06:08 CAT' },
  { id: 'received', detail: 'Received / expected', value: 'Unknown / 14,620' },
  { id: 'retained', detail: 'Data retained', value: '14,620 last-successful records' },
  { id: 'next', detail: 'Next scheduled run', value: '23 Nov 2026 · 06:00 CAT' },
];
