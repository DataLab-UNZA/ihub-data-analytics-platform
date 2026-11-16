/** Mock content for organisation, unit and comparison screens. */

/**
 * Organisation hierarchy. Nodes with `expandable` can be opened even when
 * their children are not loaded in this prototype.
 */
export const organisationTree = {
  id: 'unza',
  name: 'University of Zambia',
  kind: 'Organisation',
  outputs: '28,854',
  childrenLabel: '13 schools',
  expanded: true,
  children: [
    {
      id: 'agri',
      name: 'School of Agricultural Sciences',
      kind: 'Unit',
      outputs: '3,485',
      childrenLabel: '2 departments',
      expanded: true,
      children: [
        { id: 'crop', name: 'Crop Sciences', kind: 'Department', outputs: '1,140', childrenLabel: '0 departments' },
        { id: 'soil', name: 'Soil Science', kind: 'Department', outputs: '890', childrenLabel: '0 departments' },
      ],
    },
    {
      id: 'edu',
      name: 'School of Education',
      kind: 'Unit',
      outputs: '4,210',
      childrenLabel: '9 departments',
      expandable: true,
    },
    {
      id: 'med',
      name: 'School of Medicine',
      kind: 'Unit',
      outputs: '8,240',
      childrenLabel: '8 departments',
      expanded: true,
      selected: true,
      children: [
        { id: 'bio', name: 'Biomedical Sciences', kind: 'Department', outputs: '2,180', childrenLabel: '0 departments' },
        { id: 'ph', name: 'Public Health', kind: 'Department', outputs: '2,740', childrenLabel: '0 departments' },
      ],
    },
    {
      id: 'nat',
      name: 'School of Natural Sciences',
      kind: 'Unit',
      outputs: '5,930',
      childrenLabel: '7 departments',
      expandable: true,
    },
    {
      id: 'more',
      name: '9 more schools',
      kind: 'Unit',
      outputs: '6,989',
      childrenLabel: '9 schools',
      expandable: true,
    },
  ],
};

export const medicineKpis = [
  { label: 'Total outputs', value: '8,240', note: '+7.4% vs last period' },
  { label: 'Open access', value: '69.8%', note: '+2.6 pp vs last period' },
  { label: 'Citations', value: '54,210', note: '+9.8% vs last period' },
  { label: 'Outputs per staff', value: '29.0', note: '284 staff · illustrative manual baseline', neutral: true },
];

export const medicineSeries = [
  { label: '2015', value: 300 },
  { label: '2016', value: 680 },
  { label: '2017', value: 540 },
  { label: '2018', value: 950 },
  { label: '2019', value: 1000 },
  { label: '2020', value: 1080 },
  { label: '2021', value: 1220 },
  { label: '2022', value: 1320 },
  { label: '2023', value: 1820 },
  { label: '2024', value: 2000 },
  { label: '2025', value: 2280 },
  { label: '2026', value: 2700 },
];

export const medicineSubunits = [
  { label: 'Biomedical Sciences', value: 2180, href: '/publications' },
  { label: 'Clinical Sciences', value: 1820, tone: 'teal', href: '/publications' },
  { label: 'Nursing Sciences', value: 1500, tone: 'blue', href: '/publications' },
  { label: 'Public Health', value: 2740, href: '/publications' },
];

export const medicineJournals = [
  { id: 1, journal: 'Medical Journal of Zambia', outputs: '864' },
  { id: 2, journal: 'Zambia Health Research', outputs: '542' },
  { id: 3, journal: 'PLOS Global Public Health', outputs: '318' },
  { id: 4, journal: 'BMC Public Health', outputs: '271' },
];

export const medicineMembers = [
  { id: 1, member: 'Chanda Banda', unit: 'Public Health', orcid: 'Linked' },
  { id: 2, member: 'Diana Chileshe', unit: 'Biomedical', orcid: 'Linked' },
  { id: 3, member: 'James Phiri', unit: 'Clinical Sciences', orcid: 'Unknown' },
  { id: 4, member: 'Mary Zulu', unit: 'Nursing', orcid: 'Linked' },
];

export const comparedUnits = ['Agricultural Sciences', 'Education', 'Medicine'];

export const comparisonRows = [
  { id: 'agri', unit: 'Agricultural Sciences', outputs: '3,485', staff: '126', perStaff: '27.7', fte: '112', perFte: '31.1' },
  { id: 'edu', unit: 'Education', outputs: '4,210', staff: '185', perStaff: '22.8', fte: 'Unknown', perFte: 'Unknown' },
  { id: 'med', unit: 'Medicine', outputs: '8,240', staff: '284', perStaff: '29.0', fte: '261', perFte: '31.6' },
];

/** Outputs per staff member (illustrative five-number summaries). */
export const staffDistribution = [
  { label: 'Agricultural Sciences', tone: 'accent', min: 0, q1: 6.67, median: 18.8, q3: 30, max: 52 },
  { label: 'Education', tone: 'teal', min: 0, q1: 8.27, median: 20.8, q3: 34.27, max: 49.33 },
  { label: 'Medicine', tone: 'blue', min: 0, q1: 9.87, median: 22.8, q3: 38.53, max: 46.67 },
];
