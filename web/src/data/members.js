/** Mock content for member screens. */

export const memberDirectory = [
  { id: 'agnes-chanda', member: 'Agnes Chanda', unit: 'Education', orcid: 'Linked', records: '32' },
  { id: 'chanda-banda', member: 'Chanda Banda', unit: 'Public Health', orcid: 'Linked', records: '48' },
  { id: 'diana-chileshe', member: 'Diana Chileshe', unit: 'Biomedical Sciences', orcid: 'Linked', records: '61' },
  { id: 'james-phiri', member: 'James Phiri', unit: 'Clinical Sciences', orcid: 'Unknown', records: '29' },
  { id: 'mary-zulu', member: 'Mary Zulu', unit: 'Nursing Sciences', orcid: 'Linked', records: '37' },
  { id: 'peter-zimba', member: 'Peter Zimba', unit: 'Agricultural Sciences', orcid: 'Linked', records: '46' },
];

export const memberUnits = [
  'Unit: All',
  'Education',
  'Public Health',
  'Biomedical Sciences',
  'Clinical Sciences',
  'Nursing Sciences',
  'Agricultural Sciences',
];

export const linkedPublications = [
  { id: 1, title: 'Strengthening community health systems in Zambia', year: '2026', source: 'OpenAlex + ORCID' },
  { id: 2, title: 'Primary care access in rural communities', year: '2025', source: 'Repository' },
  { id: 3, title: 'Community-led approaches to prevention', year: '2024', source: 'Medical Journal of Zambia' },
  { id: 4, title: 'Health workforce and service delivery', year: '2024', source: 'OpenAlex' },
];

export const correctionTypes = [
  'Not my publication',
  'Wrong year or type',
  'Wrong unit',
  'Missing co-author',
  'Other',
];
