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
  { key: 'combo', label: 'Bars and Line', group: 'Evolution', hint: 'Bars for the first measure, lines for the others' },
  { key: 'pie', label: 'Pie Chart', group: 'Part of a whole', hint: 'Shares of a total' },
  { key: 'treemap', label: 'Treemap', group: 'Part of a whole', hint: 'Shares as nested rectangles' },
  { key: 'sunburst', label: 'Sunburst', group: 'Part of a whole', hint: 'Nested rings, from a broad group to the detail' },
  { key: 'heatmap', label: 'Heatmap', group: 'Correlation', hint: 'One metric across two categories' },
  { key: 'scatter', label: 'Bubble Chart', group: 'Correlation', hint: 'Two measures against each other, bubble size for a third' },
  { key: 'world_map', label: 'World Map', group: 'Map', hint: 'A metric by country (group by Country)' },
];

export const DEFAULT_OPTIONS = {
  show_legend: true,
  show_values: false,
  stacked: false,
  horizontal: false,
  donut: false,
  stack_percent: false,
  log_scale: false,
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

const label = (value) => {
  if (value === null || value === undefined) return '(empty)';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

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
      // With no group-by column each metric becomes a bar (for example, shares of complete records).
      return need(metrics.length >= 1 && (dims.length >= 1 || result.rows.length === 1), 'Add a metric and a group-by column.');
    case 'line':
    case 'area':
    case 'pie':
    case 'treemap':
    case 'combo':
    case 'sunburst':
      return need(dims.length >= 1 && metrics.length >= 1, 'Add a metric and a group-by column.');
    case 'scatter':
      return need(dims.length >= 1 && metrics.length >= 2, 'A bubble chart needs a group-by column and two or three metrics.');
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
  if (dims.length === 0) return metricBars(result, opts);
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

  const percentStack = Boolean(opts.stacked && opts.stack_percent && series.length > 1);
  if (percentStack) {
    // Every bar adds up to 100%: show each series as its share of that category.
    const totals = categories.map((_, i) => series.reduce((sum, item) => sum + (item.values[i] ?? 0), 0));
    series = series.map((item) => ({ ...item, values: item.values.map((v, i) => (v === null || !totals[i] ? null : v / totals[i])) }));
  }
  const format = percentStack ? 'percent' : metric.format;
  const horizontal = kind === 'bar' && opts.horizontal;
  const valueAxis = {
    type: opts.log_scale && !percentStack ? 'log' : 'value',
    name: opts.y_label || (series.length === 1 ? metric.label : ''),
    nameLocation: 'middle',
    nameGap: 48,
    max: percentStack ? 1 : undefined,
    axisLabel: { formatter: (v) => formatValue(v, format) },
  };
  const categoryAxis = {
    type: 'category',
    data: categories,
    name: horizontal && !opts.x_label ? '' : opts.x_label || x.label,
    nameLocation: 'middle',
    nameGap: 32,
    axisLabel: {
      hideOverlap: true,
      rotate: !horizontal && categories.length > 12 && x.type === 'string' ? 35 : 0,
      ...(horizontal ? { width: 170, overflow: 'truncate' } : {}),
    },
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
      stack: opts.stacked || percentStack ? 'total' : undefined,
      areaStyle: kind === 'area' ? { opacity: 0.35 } : undefined,
      smooth: false,
      showSymbol: kind !== 'bar' && categories.length < 40,
      label: opts.show_values ? { show: true, position: opts.stacked ? 'inside' : 'top', formatter: (p) => formatValue(p.value, format) } : undefined,
      emphasis: { focus: 'series' },
      barMaxWidth: 48,
    })),
  };
}


/** Bars with one bar per metric (no group-by column), for example the share of records with each field. */
function metricBars(result, opts) {
  const { metrics } = splitColumns(result);
  const row = result.rows[0] ?? [];
  const format = metrics[0].format;
  const horizontal = opts.horizontal;
  const names = metrics.map((m) => m.label);
  const values = metrics.map((m) => row[m.index] ?? null);
  const categoryAxis = { type: 'category', data: names, axisLabel: { interval: 0, width: 150, overflow: 'truncate' } };
  const valueAxis = { type: 'value', axisLabel: { formatter: (v) => formatValue(v, format) }, max: format === 'percent' ? 1 : undefined };
  return {
    grid: { left: 24, right: 24, top: 24, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => formatValue(v, format, { full: true }) },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: [{ type: 'bar', data: values, barMaxWidth: 64, label: { show: true, position: horizontal ? 'right' : 'top', formatter: (p) => formatValue(p.value, format) } }],
  };
}

/** Bars for the first metric and lines for the others; a second axis when the units differ. */
function comboChart(result, opts) {
  const { dims, metrics } = splitColumns(result);
  const [x] = dims;
  const rows = [...result.rows];
  if (x.type === 'year' || x.type === 'number') rows.sort((a, b) => (a[x.index] ?? 0) - (b[x.index] ?? 0));
  const categories = rows.map((row) => label(row[x.index]));
  const [first, ...others] = metrics;
  const top = (m) => Math.max(0, ...rows.map((row) => Math.abs(row[m.index] ?? 0)));
  // A line needs its own axis when its unit differs (a share against a count) or it is dwarfed by the bars.
  const apart = (m) => (m.format === 'percent') !== (first.format === 'percent') || top(first) > 8 * top(m) || top(m) > 8 * top(first);
  const secondary = others.some(apart);
  const axis = (m, position) => ({
    type: 'value',
    name: m.label,
    nameLocation: 'middle',
    nameGap: 48,
    position,
    axisLabel: { formatter: (v) => formatValue(v, m.format) },
    splitLine: { show: position !== 'right' },
  });
  const sideMetric = others.find(apart);
  return {
    grid: { left: 64, right: secondary ? 64 : 24, top: opts.show_legend ? 48 : 24, bottom: 56, containLabel: true },
    legend: opts.show_legend ? { type: 'scroll', top: 0, right: 0 } : undefined,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v) => (v === null || v === undefined ? '–' : String(v)) },
    xAxis: { type: 'category', data: categories, name: opts.x_label || x.label, nameLocation: 'middle', nameGap: 32, axisLabel: { hideOverlap: true, rotate: categories.length > 12 && x.type === 'string' ? 35 : 0, width: 110, overflow: 'truncate' } },
    yAxis: secondary ? [axis(first, 'left'), axis(sideMetric, 'right')] : axis(first, 'left'),
    series: metrics.map((m, i) => ({
      name: m.label,
      type: i === 0 ? 'bar' : 'line',
      yAxisIndex: secondary && i > 0 && apart(m) ? 1 : 0,
      data: rows.map((row) => row[m.index] ?? null),
      barMaxWidth: 48,
      showSymbol: categories.length < 40,
      connectNulls: false,
      tooltip: { valueFormatter: (v) => formatValue(v, m.format, { full: true }) },
    })),
  };
}

const SCHOOL_PREFIX = /^(School of|Institute of|Directorate of|Graduate School of)\s+/;

/** Bubbles: first metric across, second up, third (optional) as the bubble size. */
function bubbleChart(result, opts) {
  const { dims, metrics } = splitColumns(result);
  const [xMetric, yMetric, sizeMetric] = metrics;
  const points = result.rows
    .map((row) => ({ name: label(row[dims[0].index]), x: row[xMetric.index], y: row[yMetric.index], size: sizeMetric ? row[sizeMetric.index] : null }))
    .filter((p) => p.x !== null && p.y !== null);
  const sizes = points.map((p) => p.size ?? 0);
  const [low, high] = [Math.min(...sizes), Math.max(...sizes)];
  const scale = (v) => (sizeMetric && high > low ? 14 + (36 * (v - low)) / (high - low) : 22);
  return {
    grid: { left: 64, right: 32, top: 24, bottom: 56, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p) =>
        [`<strong>${p.data.name}</strong>`, `${xMetric.label}: ${formatValue(p.data.value[0], xMetric.format, { full: true })}`, `${yMetric.label}: ${formatValue(p.data.value[1], yMetric.format, { full: true })}`]
          .concat(sizeMetric ? [`${sizeMetric.label}: ${formatValue(p.data.value[2], sizeMetric.format, { full: true })}`] : [])
          .join('<br/>'),
    },
    xAxis: { type: 'value', name: xMetric.label, nameLocation: 'middle', nameGap: 32, scale: true, axisLabel: { formatter: (v) => formatValue(v, xMetric.format) } },
    yAxis: { type: 'value', name: yMetric.label, nameLocation: 'middle', nameGap: 48, scale: true, axisLabel: { formatter: (v) => formatValue(v, yMetric.format) } },
    series: [
      {
        type: 'scatter',
        data: points.map((p) => ({ name: p.name, value: [p.x, p.y, p.size ?? 0] })),
        symbolSize: (value) => scale(value[2]),
        itemStyle: { opacity: 0.75 },
        label: { show: true, position: 'right', formatter: (p) => p.name.replace(SCHOOL_PREFIX, ''), fontSize: 11 },
        labelLayout: { hideOverlap: true },
        emphasis: { focus: 'self', label: { show: true } },
      },
    ],
  };
}

/** Rings from the first group-by column (inside) to the last (outside). */
function sunburstChart(result) {
  const { dims, metrics } = splitColumns(result);
  const metric = metrics[0];
  const root = new Map();
  for (const row of result.rows) {
    let level = root;
    dims.forEach((dim, depth) => {
      const name = label(row[dim.index]);
      if (!level.has(name)) level.set(name, { name, children: new Map(), value: 0 });
      const node = level.get(name);
      if (depth === dims.length - 1) node.value += row[metric.index] ?? 0;
      level = node.children;
    });
  }
  const toData = (level) =>
    [...level.values()].map((node) => (node.children.size ? { name: node.name, children: toData(node.children) } : { name: node.name, value: node.value }));
  return {
    tooltip: { trigger: 'item', valueFormatter: (v) => formatValue(v, metric.format, { full: true }) },
    series: [
      {
        type: 'sunburst',
        data: toData(root),
        radius: ['12%', '95%'],
        sort: undefined,
        label: { rotate: 'radial', minAngle: 8, fontSize: 11 },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { focus: 'ancestor' },
        levels: [{}, { r0: '12%', r: '38%', label: { rotate: 'tangential' } }, { r0: '38%', r: '68%', label: { minAngle: 10 } }, { r0: '68%', r: '95%', label: { show: false } }].slice(0, dims.length + 1),
      },
    ],
  };
}

/**
 * A height that suits the chart: tall lists of bars and heatmaps need room for every label.
 *
 * @param {string} viz The chart type.
 * @param {object} result The query result.
 * @param {object} options Customise options.
 */
export function suggestedHeight(viz, result, options = {}) {
  const rows = result?.row_count ?? 0;
  const { dims } = splitColumns(result);
  const categories = dims[0] ? new Set(result.rows.map((row) => row[dims[0].index])).size : 0;
  if (viz === 'bar' && options.horizontal) return Math.min(900, Math.max(360, categories * 30 + 120));
  if (viz === 'heatmap' && dims[1]) {
    const ys = new Set(result.rows.map((row) => row[dims[1].index])).size;
    return Math.min(900, Math.max(400, ys * 26 + 170));
  }
  if (viz === 'sunburst' || viz === 'scatter') return 520;
  if (viz === 'world_map') return 460;
  return rows ? 420 : 420;
}

/** The ECharts option for a result, or null for chart types drawn without ECharts. */
export function buildOption(viz, result, options = {}) {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  if (!result || requirementProblem(viz, result) || viz === 'table' || viz === 'big_number') return null;
  const { dims, metrics } = splitColumns(result);
  const metric = metrics[0];
  const pairs = dims[0] ? result.rows.map((row) => ({ name: label(row[dims[0].index]), value: row[metric.index] })) : [];

  switch (viz) {
    case 'bar':
    case 'line':
    case 'area':
      return axisSeries(result, opts, viz);
    case 'combo':
      return comboChart(result, opts);
    case 'scatter':
      return bubbleChart(result, opts);
    case 'sunburst':
      return sunburstChart(result);
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
        grid: { left: 24, right: 24, top: 16, bottom: 72, containLabel: true },
        xAxis: { type: 'category', data: xs, name: x.label, nameLocation: 'middle', nameGap: xs.length > 8 ? 70 : 32, splitArea: { show: true }, axisLabel: { interval: 0, rotate: xs.length > 8 ? 40 : 0, width: 130, overflow: 'truncate' } },
        yAxis: { type: 'category', data: ys, splitArea: { show: true }, axisLabel: { interval: 0, width: 170, overflow: 'truncate' } },
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
