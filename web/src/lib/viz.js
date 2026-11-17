/**
 * Chart types and how a query result becomes an Apache ECharts option, in the style of
 * Apache Superset. Pure functions: the same result always draws the same chart, on Explore
 * and on dashboards.
 *
 * A result has `columns` ({key, label, type, is_metric, format}) and `rows` (arrays in
 * column order), as returned by /api/explore/query.
 */
import { countryName } from '@/lib/countries';

export const VIZ_TYPES = [
  { key: 'table', label: 'Table', group: 'Table', hint: 'Rows and columns, sortable' },
  { key: 'big_number', label: 'Big Number', group: 'KPI', hint: 'One headline value, with a trend over years' },
  { key: 'bar', label: 'Bar Chart', group: 'Evolution', hint: 'Compare values across a category or over years' },
  { key: 'line', label: 'Line Chart', group: 'Evolution', hint: 'A trend over years' },
  { key: 'area', label: 'Area Chart', group: 'Evolution', hint: 'A trend with its volume, stackable' },
  { key: 'pie', label: 'Pie Chart', group: 'Part of a whole', hint: 'Shares of a total' },
  { key: 'treemap', label: 'Treemap', group: 'Part of a whole', hint: 'Shares as nested rectangles' },
  { key: 'heatmap', label: 'Heatmap', group: 'Correlation', hint: 'One metric across two categories' },
  { key: 'world_map', label: 'World Map', group: 'Map', hint: 'A metric by country (group by Country)' },
];

export const DEFAULT_OPTIONS = {
  show_legend: true,
  show_values: false,
  stacked: false,
  horizontal: false,
  donut: false,
  x_label: '',
  y_label: '',
  subheader: '',
};

const compact = new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 2 });
const whole = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });
const percent = new Intl.NumberFormat('en-GB', { style: 'percent', maximumFractionDigits: 1 });

/** A value as Superset would show it: compact numbers (6.19k), percentages, plain text. */
export function formatValue(value, format = 'number', { full = false } = {}) {
  if (value === null || value === undefined) return '–';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value !== 'number') return String(value);
  if (format === 'percent') return percent.format(value);
  if (format === 'decimal') return decimal.format(value);
  if (full || Math.abs(value) < 1000) return Number.isInteger(value) ? whole.format(value) : decimal.format(value);
  return compact.format(value).toLowerCase();
}

export function splitColumns(result) {
  const columns = result?.columns ?? [];
  return {
    dims: columns.map((c, i) => ({ ...c, index: i })).filter((c) => !c.is_metric),
    metrics: columns.map((c, i) => ({ ...c, index: i })).filter((c) => c.is_metric),
  };
}

const label = (value) => (value === null || value === undefined ? '(empty)' : String(value));

/** What a chart type needs, as a message, or null when the result fits. */
export function requirementProblem(viz, result) {
  if (!result) return null;
  const { dims, metrics } = splitColumns(result);
  const need = (cond, message) => (cond ? null : message);
  switch (viz) {
    case 'table':
      return null;
    case 'big_number':
      return need(metrics.length >= 1, 'A Big Number needs a metric.');
    case 'bar':
    case 'line':
    case 'area':
    case 'pie':
    case 'treemap':
      return need(dims.length >= 1 && metrics.length >= 1, 'Add a metric and a group-by column.');
    case 'heatmap':
      return need(dims.length >= 2 && metrics.length >= 1, 'A heatmap needs two group-by columns and a metric.');
    case 'world_map':
      return need(
        dims.length >= 1 && metrics.length >= 1 && dims[0].label === 'Country',
        'A world map needs Country as the first group-by column and a metric.',
      );
    default:
      return 'Choose a chart type.';
  }
}

function axisSeries(result, opts, kind) {
  const { dims, metrics } = splitColumns(result);
  const [x] = dims;
  const rows = [...result.rows];
  if (x.type === 'year' || x.type === 'number') rows.sort((a, b) => (a[x.index] ?? 0) - (b[x.index] ?? 0));
  const categories = [...new Set(rows.map((row) => label(row[x.index])))];
  const metric = metrics[0];

  let series;
  if (dims.length >= 2) {
    // Pivot: one series per value of the second group-by column, first metric.
    const by = dims[1];
    const groups = new Map();
    for (const row of rows) {
      const key = label(row[by.index]);
      if (!groups.has(key)) groups.set(key, new Map());
      groups.get(key).set(label(row[x.index]), row[metric.index]);
    }
    series = [...groups.entries()].map(([name, values]) => ({ name, values: categories.map((c) => values.get(c) ?? null) }));
  } else {
    series = metrics.map((m) => {
      const values = new Map(rows.map((row) => [label(row[x.index]), row[m.index]]));
      return { name: m.label, values: categories.map((c) => values.get(c) ?? null) };
    });
  }

  const format = metric.format;
  const horizontal = kind === 'bar' && opts.horizontal;
  const valueAxis = {
    type: 'value',
    name: opts.y_label || (series.length === 1 ? metric.label : ''),
    nameLocation: 'middle',
    nameGap: 48,
    axisLabel: { formatter: (v) => formatValue(v, format) },
  };
  const categoryAxis = {
    type: 'category',
    data: categories,
    name: opts.x_label || x.label,
    nameLocation: 'middle',
    nameGap: 32,
    axisLabel: { hideOverlap: true, rotate: !horizontal && categories.length > 12 && x.type === 'string' ? 35 : 0 },
  };
  return {
    grid: { left: 64, right: 24, top: opts.show_legend ? 48 : 24, bottom: 56, containLabel: true },
    legend: opts.show_legend ? { type: 'scroll', top: 0, right: 0 } : undefined,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: kind === 'bar' ? 'shadow' : 'line' },
      valueFormatter: (v) => formatValue(v, format, { full: true }),
    },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: series.map((s) => ({
      name: s.name,
      type: kind === 'area' ? 'line' : kind,
      data: s.values,
      stack: opts.stacked ? 'total' : undefined,
      areaStyle: kind === 'area' ? { opacity: 0.35 } : undefined,
      smooth: false,
      showSymbol: kind !== 'bar' && categories.length < 40,
      label: opts.show_values ? { show: true, position: opts.stacked ? 'inside' : 'top', formatter: (p) => formatValue(p.value, format) } : undefined,
      emphasis: { focus: 'series' },
      barMaxWidth: 48,
    })),
  };
}

/** The ECharts option for a result, or null for chart types drawn without ECharts. */
export function buildOption(viz, result, options = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  if (!result || requirementProblem(viz, result) || viz === 'table' || viz === 'big_number') return null;
  const { dims, metrics } = splitColumns(result);
  const metric = metrics[0];
  const pairs = result.rows.map((row) => ({ name: label(row[dims[0].index]), value: row[metric.index] }));

  switch (viz) {
    case 'bar':
    case 'line':
    case 'area':
      return axisSeries(result, opts, viz);
    case 'pie':
      return {
        legend: opts.show_legend ? { type: 'scroll', top: 0, right: 0 } : undefined,
        tooltip: { trigger: 'item', valueFormatter: (v) => formatValue(v, metric.format, { full: true }) },
        series: [
          {
            type: 'pie',
            radius: opts.donut ? ['42%', '70%'] : '70%',
            center: ['50%', '55%'],
            data: pairs,
            label: { formatter: opts.show_values ? '{b}: {d}%' : '{b}' },
            itemStyle: { borderColor: '#fff', borderWidth: 1 },
          },
        ],
      };
    case 'treemap':
      return {
        tooltip: { valueFormatter: (v) => formatValue(v, metric.format, { full: true }) },
        series: [
          {
            type: 'treemap',
            data: pairs,
            roam: false,
            breadcrumb: { show: false },
            label: { formatter: '{b}' },
            itemStyle: { borderColor: '#fff', borderWidth: 2, gapWidth: 2 },
          },
        ],
      };
    case 'heatmap': {
      const [x, y] = dims;
      const xs = [...new Set(result.rows.map((r) => label(r[x.index])))].sort();
      const ys = [...new Set(result.rows.map((r) => label(r[y.index])))];
      const values = result.rows.map((r) => r[metric.index] ?? 0);
      return {
        tooltip: { valueFormatter: (v) => formatValue(v, metric.format, { full: true }) },
        grid: { left: 140, right: 24, top: 16, bottom: 72 },
        xAxis: { type: 'category', data: xs, name: x.label, nameLocation: 'middle', nameGap: 32, splitArea: { show: true } },
        yAxis: { type: 'category', data: ys, splitArea: { show: true } },
        visualMap: {
          min: Math.min(...values),
          max: Math.max(...values),
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: 0,
          inRange: { color: ['#e9f4f7', '#1FA8C9', '#454E7C'] },
        },
        series: [
          {
            type: 'heatmap',
            data: result.rows.map((r) => [xs.indexOf(label(r[x.index])), ys.indexOf(label(r[y.index])), r[metric.index]]),
            label: { show: opts.show_values, formatter: (p) => formatValue(p.value[2], metric.format) },
          },
        ],
      };
    }
    case 'world_map': {
      // Cap the colour scale at the 90th percentile, so one dominant country (often Zambia
      // itself) does not wash out the differences between the others.
      const values = pairs.map((p) => p.value ?? 0).sort((a, b) => a - b);
      const cap = values.length ? values[Math.floor((values.length - 1) * 0.9)] : 1;
      return {
        tooltip: {
          trigger: 'item',
          formatter: (p) => `${countryName(p.name)}: ${p.value === undefined || Number.isNaN(p.value) ? 'no data' : formatValue(p.value, metric.format, { full: true })}`,
        },
        visualMap: {
          min: 0,
          max: Math.max(1, cap),
          left: 16,
          bottom: 16,
          calculable: true,
          formatter: (v) => formatValue(v, metric.format),
          text: [`${formatValue(cap, metric.format)}+`, '0'],
          inRange: { color: ['#d6eef5', '#1FA8C9', '#454E7C'] },
        },
        series: [
          {
            type: 'map',
            map: 'world',
            roam: true,
            data: pairs,
            itemStyle: { areaColor: '#e5e5e5', borderColor: '#fff', borderWidth: 0.5 },
            emphasis: { label: { show: false }, itemStyle: { areaColor: '#FCC700' } },
          },
        ],
      };
    }
    default:
      return null;
  }
}
