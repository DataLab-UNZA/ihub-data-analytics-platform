/** Mock content for the overview screens. Replace with API calls when the back end exists. */

export const overviewKpis = [
  { label: 'Total outputs', value: '28,854', note: '+8.2% vs last period' },
  { label: 'Open access', value: '64.2%', note: '+3.1 pp vs last period' },
  { label: 'Citations', value: '158,420', note: '+11.4% vs last period' },
  { label: 'Outputs per staff', value: 'Unknown', note: 'Organisation baseline incomplete', neutral: true },
];

export const outputSeries = [
  { label: '2015', value: 700 },
  { label: '2016', value: 1000 },
  { label: '2017', value: 870 },
  { label: '2018', value: 1270 },
  { label: '2019', value: 1150 },
  { label: '2020', value: 1700 },
  { label: '2021', value: 1550 },
  { label: '2022', value: 2000 },
  { label: '2023', value: 1820 },
  { label: '2024', value: 2420 },
  { label: '2025', value: 2220 },
  { label: '2026', value: 2750 },
];

export const unitTotals = [
  { label: 'Agricultural Sciences', value: 3485 },
  { label: 'Education', value: 4210, tone: 'teal' },
  { label: 'Medicine', value: 8240, tone: 'blue' },
  { label: 'Natural Sciences', value: 5930 },
];

export const topJournals = [
  { id: 'mjz', journal: 'Medical Journal of Zambia', outputs: '1,264' },
  { id: 'ujs', journal: 'UNZA Journal of Science', outputs: '982' },
  { id: 'zssj', journal: 'Zambia Social Science Journal', outputs: '746' },
  { id: 'joa', journal: 'Journal of Agriculture', outputs: '528' },
];

/** Collaborating countries, positioned as percentages of the world map. */
export const collaborationPins = [
  { name: 'United States', x: '22.2%', y: '27.1%' },
  { name: 'United Kingdom', x: '49.4%', y: '17.5%' },
  { name: 'China', x: '79.2%', y: '28.9%' },
  { name: 'Australia', x: '87.2%', y: '65%' },
  { name: 'Zambia', label: 'Zambia, 8,420 collaborations', x: '57.8%', y: '57.8%', large: true },
];

export const loadingKpiTitles = ['Total outputs', 'Open access', 'Citations', 'Outputs per staff'];
export const loadingBarHeights = ['20%', '30%', '42%', '37%', '62%', '78%', '84%', '98%'];
