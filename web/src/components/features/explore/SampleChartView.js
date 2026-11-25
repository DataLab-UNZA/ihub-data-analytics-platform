'use client';

import Link from 'next/link';
import { Alert, Collapse } from 'antd';
import ChartView, { ResultTable } from '@/components/charts/ChartView';
import { DEFAULT_OPTIONS, suggestedHeight } from '@/lib/viz';

/**
 * A sample chart, laid out like a ready-made research chart (GuideView) but with fixed,
 * made-up numbers: no filters, saving or download, and a clear note that it is a sample.
 *
 * @param {object} chart   A sample chart from src/data/sample-charts.json.
 * @param {object} chartModule Its module (src/config/chart-modules.js).
 * @param {Array}  related The module's other sample charts.
 */
export default function SampleChartView({ chart, chartModule, related }) {
  const options = { ...DEFAULT_OPTIONS, ...chart.options };
  return (
    <div className="guide">
      <nav className="guide__crumbs" aria-label="Breadcrumb">
        <Link href={`/explore#module-${chartModule.key}`}>← All ready-made charts</Link>
        <span aria-hidden="true">·</span>
        <span>{chartModule.title}</span>
      </nav>

      <header className="guide__head">
        <h1 className="guide__title">{chart.title}</h1>
        <p className="guide__question">{chart.question}</p>
      </header>

      <Alert
        className="sample-note"
        type="info"
        showIcon
        title="Sample data"
        description={`These numbers are made up to show what this chart will look like. The ${chartModule.title.toLowerCase()} module is not connected yet.`}
      />

      <section className="guide__chart" aria-label={chart.title}>
        <ChartView viz={chart.viz} result={chart.result} options={options} height={suggestedHeight(chart.viz, chart.result, options)} />
      </section>

      <div className="guide__explain">
        <section aria-labelledby="how-title">
          <h2 id="how-title">How to read this chart</h2>
          <p>{chart.how_to_read}</p>
        </section>
      </div>

      <Collapse
        ghost
        className="guide__numbers"
        items={[{ key: 'numbers', label: 'See the numbers behind the chart', children: <ResultTable result={chart.result} height={320} pageSize={12} /> }]}
      />

      {related.length > 0 && (
        <section className="guide__related" aria-labelledby="related-title">
          <h2 id="related-title">More in {chartModule.title}</h2>
          <ul>
            {related.map((other) => (
              <li key={other.id}>
                <Link href={`/explore/sample/${other.id}`}>{other.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
