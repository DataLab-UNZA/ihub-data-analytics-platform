/** Mock content for publication screens. */

export const publicationRows = [
  { id: 1, title: 'Strengthening community health systems in Zambia', year: '2026', oa: 'Yes', sources: '3' },
  { id: 2, title: 'Climate resilience and smallholder agriculture', year: '2026', oa: 'Yes', sources: '2' },
  { id: 3, title: 'Digital learning in higher education', year: '2025', oa: 'No', sources: '2' },
  { id: 4, title: 'Biodiversity across the Zambezi basin', year: '2025', oa: 'Yes', sources: '3' },
  { id: 5, title: 'Health workforce and service delivery', year: '2024', oa: 'Unknown', sources: '1' },
];

export const savedSearches = [
  { label: 'Open access outputs', description: 'All units · OA only', href: '/publications' },
  { label: 'Repository opportunities', description: 'Not found in repository', href: '/coverage' },
];

export const oaOptions = ['OA: All', 'OA: Yes', 'OA: No', 'OA: Unknown'];
export const repositoryOptions = ['Repository: All', 'Repository: Found', 'Repository: Not found'];

export const recordMetadata = [
  { id: 'year', field: 'Year / type', href: '/publications', value: '2026 · Journal article' },
  { id: 'journal', field: 'Journal', href: '/journals', value: 'Medical Journal of Zambia' },
  { id: 'doi', field: 'DOI', href: '/publications', value: 'Unknown' },
  { id: 'unit', field: 'Unit', href: '/organisation/medicine', value: 'Public Health / Medicine' },
  { id: 'oa', field: 'Open access', href: '/publications', value: 'Yes · source supplied' },
];

export const recordAuthors = ['Chanda Banda', 'Diana Chileshe', 'Mary Zulu'];

export const searchResults = [
  {
    id: 1,
    kind: 'Publication',
    title: 'Strengthening community health systems in Zambia',
    href: '/publications/example-record',
    meta: '2026 · Medical Journal of Zambia · OpenAlex, ORCID, journal',
  },
  {
    id: 2,
    kind: 'Publication',
    title: 'Community-led approaches to prevention',
    href: '/publications/example-record',
    meta: '2024 · Repository, OpenAlex',
  },
  { id: 3, kind: 'Unit', title: 'Public Health', href: '/organisation/medicine', meta: 'School of Medicine · 2,740 outputs' },
  {
    id: 4,
    kind: 'Member · authorised',
    title: 'Chanda Banda',
    href: '/members/chanda-banda',
    meta: 'Public Health · ORCID linked',
  },
];
