'use client';

import { Empty, Table } from 'antd';
import EChart from './EChart';
import { buildOption, formatValue, requirementProblem, splitColumns } from '@/lib/viz';

/** Big Number, like Superset's: the latest value, with a sparkline when grouped by year. */
function BigNumber({ result, options }) {
  const { dims, metrics } = splitColumns(result);
  const metric = metrics[0];
  let value = result.rows[0]?.[metric.index];
  let trend = null;
  if (dims[0] && (dims[0].type === 'year' || dims[0].type === 'number')) {
    const rows = [...result.rows].sort((a, b) => a[dims[0].index] - b[dims[0].index]);
    value = rows.at(-1)?.[metric.index];
    trend = {
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { type: 'category', show: false, data: rows.map((r) => r[dims[0].index]) },
      yAxis: { type: 'value', show: false, scale: true },
      tooltip: { trigger: 'axis', valueFormatter: (v) => formatValue(v, metric.format, { full: true }) },
      series: [{ type: 'line', data: rows.map((r) => r[metric.index]), showSymbol: false, areaStyle: { opacity: 0.15 } }],
    };
  }
  return (
    <div className="big-number">
      <p className="big-number__value" title={formatValue(value, metric.format, { full: true })}>
        {formatValue(value, metric.format)}
      </p>
      <p className="big-number__subheader">{options?.subheader || metric.label}</p>
      {trend && <EChart option={trend} height={72} ariaLabel={`${metric.label} trend`} />}
    </div>
  );
}

/** A query result as a sortable table. */
export function ResultTable({ result, height, pageSize = 50, size = 'small' }) {
  const columns = (result?.columns ?? []).map((column, index) => ({
    key: column.key,
    title: column.label,
    dataIndex: index,
    align: column.is_metric ? 'right' : 'left',
    sorter: (a, b) => {
      const x = a[index];
      const y = b[index];
      if (x === y) return 0;
      if (x === null || x === undefined) return -1;
      if (y === null || y === undefined) return 1;
      return typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y));
    },
    render: (value) => {
      if (column.is_metric) return formatValue(value, column.format, { full: true });
      if (column.type === 'year') return value ?? '–'; // 2023, never 2.02k or 2,023
      return formatValue(value, 'number', { full: true });
    },
  }));
  const data = (result?.rows ?? []).map((row, i) => Object.assign([...row], { key: i }));
  return (
    <Table
      className="result-table"
      size={size}
      columns={columns}
      dataSource={data}
      pagination={data.length > pageSize ? { pageSize, showSizeChanger: false, size: 'small' } : false}
      scroll={height ? { y: height, x: 'max-content' } : { x: 'max-content' }}
    />
  );
}

/**
 * Draws a query result as the chosen chart type.
 *
 * @param {string} viz      A key from VIZ_TYPES.
 * @param {object} result   The /api/explore/query result.
 * @param {object} options  Customise options (legend, values, stacked...).
 */
export default function ChartView({ viz, result, options, height = 400 }) {
  if (!result) {
    return <Empty description="Run the query to see the chart" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  if (result.row_count === 0) {
    return <Empty description="No results for these filters" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const problem = requirementProblem(viz, result);
  if (problem) {
    return <Empty description={problem} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  if (viz === 'table') return <ResultTable result={result} height={height - 56} />;
  if (viz === 'big_number') return <BigNumber result={result} options={options} />;
  return <EChart option={buildOption(viz, result, options)} height={height} ariaLabel={`${viz} chart`} />;
}
