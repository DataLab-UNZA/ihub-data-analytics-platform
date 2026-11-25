import samples from '@/data/sample-charts.json';

/**
 * The modules whose charts Explore and the Charts page show, in display order.
 *
 * - `live` modules read real data: their ready-made charts come from the API
 *   (/api/explore/guides) and `featured` names the guides the Charts page shows first.
 * - `sample` modules are not connected yet: their charts are made-up numbers from
 *   src/data/sample-charts.json, clearly labelled as samples, shown in Explore under `theme`.
 *
 * Adding a module is one entry here (and, while it has no source, its samples in the JSON file).
 * When a sample module is connected, switch it to `live` and list its featured guides.
 */
export const CHART_MODULES = [
  {
    key: 'research',
    title: 'Research',
    source: 'OpenAlex, ORCID, the repository and UNZA journals',
    blurb: 'Publications, citations, open access and collaboration, from the connected research sources.',
    status: 'live',
    featured: ['output-per-year', 'output-by-school'],
  },
  {
    key: 'hr',
    title: 'Human resources',
    theme: 'Staffing',
    source: 'HR system',
    blurb: 'Staff numbers and ranks. Sample data until the HR system is connected.',
    status: 'sample',
  },
  {
    key: 'students',
    title: 'Student information',
    theme: 'Enrolment',
    source: 'Student records system',
    blurb: 'Enrolment by year and school. Sample data until the student records system is connected.',
    status: 'sample',
  },
  {
    key: 'lms',
    title: 'Learning management',
    theme: 'Engagement',
    source: 'Moodle',
    blurb: 'How students use Moodle, the learning platform. Sample data until Moodle is connected.',
    status: 'sample',
  },
];

/** The sample charts of a module (an empty list for a live module). */
export const sampleCharts = (moduleKey) => samples[moduleKey] ?? [];

/** One sample chart by id, or null. */
export const sampleChart = (id) => findSampleChart(id)?.chart ?? null;

/** One sample chart by id, with its module, or null. */
export function findSampleChart(id) {
  for (const chartModule of CHART_MODULES) {
    const chart = sampleCharts(chartModule.key).find((item) => item.id === id);
    if (chart) return { chart, chartModule };
  }
  return null;
}

/** Where a chart opens: a live guide or a sample chart page. */
export const chartHref = (chart, chartModule) =>
  chartModule.status === 'sample' ? `/explore/sample/${chart.id}` : `/explore/guide/${chart.id}`;
