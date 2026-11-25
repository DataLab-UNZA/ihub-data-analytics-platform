'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Alert, Button, Spin, Tag } from 'antd';
import { ArrowRightOutlined, CompassOutlined } from '@ant-design/icons';
import ChartView from '@/components/charts/ChartView';
import { bff } from '@/components/features/explore/client';
import { guideSpec } from '@/lib/guides';
import { DEFAULT_OPTIONS } from '@/lib/viz';

const CHART_HEIGHT = 320;

/** A live ready-made chart: runs its query once, with no filters. Also used by the dashboard. */
export function LiveChart({ guide, height = CHART_HEIGHT }) {
  const spec = useMemo(() => guideSpec(guide), [guide]);
  const [state, setState] = useState({ result: null, error: null, loading: true });

  useEffect(() => {
    let active = true;
    bff('explore/query', { method: 'POST', body: spec })
      .then((result) => active && setState({ result, error: null, loading: false }))
      .catch((err) => active && setState({ result: null, error: err.message, loading: false }));
    return () => {
      active = false;
    };
  }, [spec]);

  if (state.error) return <Alert type="error" showIcon title="The chart could not be drawn" description={state.error} />;
  return (
    <Spin spinning={state.loading}>
      <ChartView viz={guide.viz} result={state.result} options={{ ...DEFAULT_OPTIONS, ...guide.options }} height={height} />
    </Spin>
  );
}

/** One chart card: title, question, the chart and a link to it in Explore. */
function ChartCard({ chart, sample }) {
  return (
    <article className="card featured-chart" aria-labelledby={`chart-${chart.id}`}>
      <header className="card__head">
        <h3 className="card__title" id={`chart-${chart.id}`}>
          <Link href={chart.href}>{chart.title}</Link>
        </h3>
        <p className="card__sub">{chart.question}</p>
      </header>
      <div className="featured-chart__body">
        {sample ? (
          <ChartView viz={chart.viz} result={chart.result} options={{ ...DEFAULT_OPTIONS, ...chart.options }} height={CHART_HEIGHT} />
        ) : (
          <LiveChart guide={chart} />
        )}
      </div>
      <footer className="featured-chart__foot">
        <Link href={chart.href}>
          Open in Explore <ArrowRightOutlined />
        </Link>
      </footer>
    </article>
  );
}

/**
 * The Charts page's main charts, grouped by module: the most used research charts (live) and
 * two sample charts for each module that is not connected yet. It ends with a way into
 * Explore, where every chart is.
 *
 * @param {Array} modules From loadFeatured(): { key, title, blurb, status, charts }.
 */
export default function FeaturedCharts({ modules }) {
  return (
    <div className="featured">
      {modules.map((chartModule) => {
        const sample = chartModule.status === 'sample';
        return (
          <section className="featured__module" key={chartModule.key} aria-labelledby={`module-${chartModule.key}`}>
            <header className="featured__head">
              <div>
                <h2 className="featured__title" id={`module-${chartModule.key}`}>
                  {chartModule.title}
                  {sample && <Tag className="featured__tag">Sample data</Tag>}
                </h2>
                <p className="featured__blurb">{chartModule.blurb}</p>
              </div>
              <Link className="featured__more" href={`/explore#module-${chartModule.key}`}>
                All {chartModule.title.toLowerCase()} charts <ArrowRightOutlined />
              </Link>
            </header>
            <div className="grid grid--halves">
              {chartModule.charts.map((chart) => (
                <ChartCard key={chart.id} chart={chart} sample={sample} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

/** The end of the Charts page: a way into Explore for more charts and more detail. */
export function ExploreCallout() {
  return (
    <section className="card explore-callout" aria-labelledby="explore-callout-title">
      <span className="explore-callout__icon" aria-hidden="true">
        <CompassOutlined />
      </span>
      <div className="explore-callout__text">
        <h2 id="explore-callout-title">Looking for more?</h2>
        <p>
          Explore has every ready-made chart, grouped by module, with filters, plain-language explanations and the numbers
          behind each chart.
        </p>
      </div>
      <Button type="primary" size="large" href="/explore">
        Go to Explore <ArrowRightOutlined />
      </Button>
    </section>
  );
}
