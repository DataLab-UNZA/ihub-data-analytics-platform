import { CHART_MODULES, sampleChart } from '@/config/chart-modules';
import { optional } from '@/lib/api';
import { formatNumber, formatShare } from '@/lib/format';
import { formatRefreshed } from '@/lib/shell-data';
import { loadOverview } from '@/services/overview';
import { loadSources } from '@/services/research';

/** Years with fewer publications than this give an open-access share too noisy to plot. */
const MIN_YEAR_PUBLICATIONS = 50;
const OA_YEARS = 15;

/** How far back the IRIMS chart of student dissertations and theses goes. */
const IRIMS_YEARS = 15;

/**
 * Students' own research in IRIMS, UNZA's institutional repository: dissertations and theses
 * per year. This is live data (IRIMS is a connected research source), queried in the browser.
 */
function irimsStudentWorks() {
  return {
    id: 'irims-student-works',
    title: 'Student dissertations and theses',
    question: 'How many student dissertations and theses reach IRIMS each year? Recent years are still being deposited.',
    source: 'IRIMS',
    area: 'Student information',
    status: 'live',
    href: '/data-sources/repository',
    viz: 'bar',
    options: { show_legend: false, y_label: 'Dissertations and theses' },
    spec: {
      dataset: 'publications',
      metrics: ['count'],
      groupby: ['year'],
      filters: [
        { column: 'publication_type', op: 'IN', value: ['Dissertation', 'Thesis'] },
        { column: 'in_repository', op: '==', value: true },
      ],
      year_from: new Date().getFullYear() - IRIMS_YEARS,
      order_by: 'c0',
      order_desc: false,
    },
    filters: [],
  };
}

/** The sample charts the dashboard draws, with the module each belongs to and any change of chart type. */
const SAMPLE_CHARTS = [
  { id: 'lms-weekly-active-learners', moduleKey: 'lms' },
  // A narrow card: a horizontal bar keeps every rank's name readable, where a donut cuts them short.
  { id: 'hr-staff-by-rank', moduleKey: 'hr', viz: 'bar', options: { horizontal: true, show_legend: false } },
];

const moduleOf = (key) => CHART_MODULES.find((item) => item.key === key);

/** A sample result's metric summed for each value of its first column (for example, per year), oldest first. */
function totalsByFirstColumn(result) {
  const metric = result.columns.findIndex((column) => column.is_metric);
  const totals = new Map();
  for (const row of result.rows) totals.set(row[0], (totals.get(row[0]) ?? 0) + row[metric]);
  return [...totals.entries()].sort((a, b) => a[0] - b[0]).map(([, total]) => total);
}

/** The latest value of a "year, category, value" sample result for one category, for example "Academic". */
function latestFor(result, category) {
  const rows = result.rows.filter((row) => row[1] === category).sort((a, b) => a[0] - b[0]);
  return rows.at(-1)?.[2] ?? 0;
}

const change = (now, before) => (before ? (now - before) / before : 0);
const signedShare = (value) => `${value >= 0 ? '+' : '−'}${formatShare(Math.abs(value))}`;

/** Open-access share per year as an explore result, so it draws with the shared chart component. */
function oaResult(perYear) {
  const rows = perYear
    .filter((row) => row.publications >= MIN_YEAR_PUBLICATIONS)
    .slice(-OA_YEARS)
    .map((row) => [row.year, row.open_access_share]);
  return {
    columns: [
      { key: 'c0', label: 'Year', type: 'year', is_metric: false, format: 'number' },
      { key: 'm0', label: 'Open-access share', type: 'number', is_metric: true, format: 'percent' },
    ],
    rows,
    row_count: rows.length,
  };
}

/** Headline figures for the modules that show sample data, worked out from their sample charts. */
function sampleFigures() {
  const enrolment = sampleChart('sis-enrolment-per-year').result;
  const students = totalsByFirstColumn(enrolment);
  const learners = sampleChart('lms-weekly-active-learners').result.rows;
  const headcount = sampleChart('hr-headcount-per-year').result;
  const staff = totalsByFirstColumn(headcount);
  return {
    students: students.at(-1),
    studentsBefore: students.at(-2),
    postgraduates: latestFor(enrolment, 'Postgraduate'),
    activeNow: learners.at(-1)[1],
    staff: staff.at(-1),
    staffBefore: staff.at(-2),
    academic: latestFor(headcount, 'Academic'),
  };
}

/** The three cards at the top of the dashboard, one per area, each leading to its charts. */
function moduleCards(research, sample) {
  return [
    {
      key: 'research',
      title: 'Research',
      source: moduleOf('research').source,
      status: 'live',
      href: '/overview',
      cta: 'Open the research overview',
      value: formatNumber(research.publications),
      valueLabel: 'research outputs',
      stats: [
        { label: 'Open access', value: formatShare(research.oaShare) },
        { label: 'Citations', value: formatNumber(research.citations) },
      ],
    },
    {
      key: 'students',
      title: 'Student information',
      source: `${moduleOf('students').source}, IRIMS and ${moduleOf('lms').source}`,
      status: 'sample',
      href: '/explore#module-students',
      cta: 'Explore student charts',
      value: formatNumber(sample.students),
      valueLabel: 'students enrolled',
      stats: [
        { label: 'Change on last year', value: signedShare(change(sample.students, sample.studentsBefore)) },
        { label: 'Active on Moodle this week', value: formatNumber(sample.activeNow) },
      ],
    },
    {
      key: 'hr',
      title: 'Human resources',
      source: moduleOf('hr').source,
      status: 'sample',
      href: '/explore#module-hr',
      cta: 'Explore HR charts',
      value: formatNumber(sample.staff),
      valueLabel: 'staff in post',
      stats: [
        { label: 'Academic staff', value: formatNumber(sample.academic) },
        { label: 'Change on last year', value: signedShare(change(sample.staff, sample.staffBefore)) },
      ],
    },
  ];
}

/** Ratios that only make sense across systems; each says which data it rests on. */
function crossModuleRatios(research, sample) {
  const latestFullYear = research.oaPerYear.filter((row) => row.publications >= MIN_YEAR_PUBLICATIONS).at(-1);
  return [
    {
      label: 'Students per academic member of staff',
      value: (sample.students / sample.academic).toFixed(1),
      basis: 'Student records and HR · sample',
    },
    {
      label: 'Enrolled students active on Moodle this week',
      value: formatShare(sample.activeNow / sample.students),
      basis: 'Moodle and student records · sample',
    },
    {
      label: 'Postgraduate share of enrolment',
      value: formatShare(sample.postgraduates / sample.students),
      basis: 'Student records · sample',
    },
    {
      label: `Research outputs per academic member of staff, ${latestFullYear?.year ?? 'latest year'}`,
      value: latestFullYear ? (latestFullYear.publications / sample.academic).toFixed(1) : '–',
      basis: 'Research live · HR sample',
    },
  ];
}

/**
 * Everything the institutional dashboard shows. Research and IRIMS are live (the overview API,
 * the source list and an explore query; research follows the global filters); student records,
 * Moodle and HR are sample data from src/data/sample-charts.json until they are connected.
 */
export async function loadDashboard(filters) {
  const [research, sources] = await Promise.all([loadOverview(filters), optional(loadSources())]);
  const sample = sampleFigures();

  const connected = (sources?.rows ?? []).map((row) => ({
    name: row.source,
    detail: `${row.publications} publications`,
    status: 'live',
  }));
  const pending = ['students', 'lms', 'hr'].map((key) => ({
    name: moduleOf(key).source,
    detail: `${moduleOf(key).title} · sample data until connected`,
    status: 'sample',
  }));

  return {
    research,
    modules: moduleCards(research, sample),
    oa: oaResult(research.oaPerYear),
    people: [
      irimsStudentWorks(),
      ...SAMPLE_CHARTS.map(({ id, moduleKey, viz, options }) => {
        const chart = sampleChart(id);
        return {
          ...chart,
          viz: viz ?? chart.viz,
          options: options ?? chart.options,
          source: moduleOf(moduleKey).source,
          area: moduleOf(moduleKey).title,
          status: 'sample',
          href: `/explore/sample/${id}`,
        };
      }),
    ],
    ratios: crossModuleRatios(research, sample),
    sources: { lastRun: formatRefreshed(sources?.lastRun ?? null), rows: [...connected, ...pending] },
  };
}
