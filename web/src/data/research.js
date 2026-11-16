/** Mock content for journals, topics, collaboration and coverage screens. */

export const journalKpis = [
  { label: 'Connected journals', value: '15', note: 'Pilot journal sources' },
  { label: 'Linked outputs', value: '7,500', note: 'Deduplicated records' },
  { label: 'Open access', value: '72.4%', note: 'Source-reported status' },
  { label: 'Coverage', value: 'Unknown', note: 'Expected corpus not supplied' },
];

export const journalDirectory = [
  { id: 1, journal: 'Journal of Agriculture', issn: 'Unknown', outputs: '528', oaShare: '81.2%', updated: '16 Nov 2026' },
  { id: 2, journal: 'Medical Journal of Zambia', issn: 'Unknown', outputs: '1,264', oaShare: '74.0%', updated: '16 Nov 2026' },
  { id: 3, journal: 'UNZA Journal of Science', issn: 'Unknown', outputs: '982', oaShare: '68.7%', updated: '16 Nov 2026' },
  { id: 4, journal: 'Zambia Health Research', issn: 'Unknown', outputs: '542', oaShare: '79.0%', updated: '16 Nov 2026' },
  { id: 5, journal: 'Zambia Social Science Journal', issn: 'Unknown', outputs: '746', oaShare: '65.3%', updated: '16 Nov 2026' },
];

/** Topic counts overlap, so they are scaled against a fixed maximum. */
export const topicThemes = [
  { label: 'Public health', value: 4820, href: '/publications' },
  { label: 'Agriculture & food security', value: 3910, tone: 'teal', href: '/publications' },
  { label: 'Education & learning', value: 3240, tone: 'blue', href: '/publications' },
  { label: 'Climate & environment', value: 2870, href: '/publications' },
  { label: 'Biodiversity', value: 2160, tone: 'teal', href: '/publications' },
  { label: 'Development economics', value: 1845, tone: 'blue', href: '/publications' },
];

export const relatedThemes = ['Maternal & child health', 'Health systems', 'Infectious disease', 'Community wellbeing'];

export const collaborationKpis = [
  { label: 'Collaborative outputs', value: '8,420', note: 'Co-authored outputs' },
  { label: 'Partner organisations', value: '246', note: 'Source-linked affiliations' },
  { label: 'Countries', value: '42', note: 'Known affiliations' },
  { label: 'Unknown country', value: '318', note: 'Affiliation country missing' },
];

export const partnerOrganisations = [
  { id: 1, partner: 'Copperbelt University', outputs: '864' },
  { id: 2, partner: 'University of Cape Town', outputs: '742' },
  { id: 3, partner: 'University of Malawi', outputs: '368' },
  { id: 4, partner: 'University of Oxford', outputs: '612' },
  { id: 5, partner: 'University of Zimbabwe', outputs: '421' },
];

export const coverageKpis = [
  { label: 'OpenAlex', value: '25,840', note: 'Bibliographic records' },
  { label: 'ORCID', value: '18,920', note: 'Author-linked records' },
  { label: 'Repository', value: '14,620', note: 'Deposited outputs' },
  { label: '15 journals', value: '7,500', note: 'Journal source records' },
];

export const sourceOverlap = [
  { label: 'One source', value: 8420, tone: 'accent', href: '/publications' },
  { label: 'Two sources', value: 11260, tone: 'teal', href: '/publications' },
  { label: 'Three or more', value: 9174, tone: 'blue', href: '/publications' },
];

export const missingFromRepository = [
  { id: 1, title: 'Climate resilience and smallholder agriculture', year: '2026', foundIn: 'OpenAlex + ORCID' },
  { id: 2, title: 'Digital learning in higher education', year: '2025', foundIn: 'OpenAlex' },
  { id: 3, title: 'Health workforce and service delivery', year: '2024', foundIn: 'OpenAlex' },
];
