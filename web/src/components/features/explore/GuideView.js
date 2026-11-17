'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { Alert, Button, Collapse, Select, Spin, Tooltip } from 'antd';
import { DownloadOutlined, SaveOutlined, ToolOutlined } from '@ant-design/icons';
import ChartView, { ResultTable } from '@/components/charts/ChartView';
import { EMPTY_FILTERS, filtersToParams, guideSpec, takeaways } from '@/lib/guides';
import { DEFAULT_OPTIONS, suggestedHeight } from '@/lib/viz';
import { bff, download } from './client';
import SaveChartModal from './SaveChartModal';

/**
 * One ready-made chart: the question, a few plain filters, the chart, how to read it and what
 * stands out. The chart can be downloaded, saved, or opened in the chart builder.
 *
 * @param {object} guide The guide (see /api/explore/guides).
 * @param {object} theme Its theme (title, other guides).
 * @param {object} options Values for the filters: { years: [..], types: [..], schools: [..] }.
 * @param {object} initial Filters from the URL.
 */
export default function GuideView({ guide, theme, options, initial = EMPTY_FILTERS, canSave, canExport, canBuild, dashboards }) {
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, ...initial });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const latest = useRef(0);

  const offered = new Set(guide.filters);
  const backwards = filters.from && filters.to && Number(filters.from) > Number(filters.to);
  const spec = useMemo(() => guideSpec(guide, filters), [guide, filters]);
  const chartOptions = { ...DEFAULT_OPTIONS, ...guide.options };

  useEffect(() => {
    if (backwards) return undefined;
    const ticket = ++latest.current;
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- show the spinner while a new query runs
    setLoading(true);
    bff('explore/query', { method: 'POST', body: spec })
      .then((data) => {
        if (active && ticket === latest.current) {
          setResult(data);
          setError(null);
        }
      })
      .catch((err) => active && ticket === latest.current && setError(err.message))
      .finally(() => active && ticket === latest.current && setLoading(false));
    return () => {
      active = false;
    };
  }, [spec, backwards]);

  const set = (key) => (value) => setFilters((current) => ({ ...current, [key]: value ?? '' }));
  const changed = Object.values(filters).some(Boolean);
  const yearOptions = options.years.map((year) => ({ value: String(year), label: String(year) }));

  const exportCsv = async () => {
    const response = await fetch('/bff/explore/query.csv', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(spec) });
    if (response.ok) download(await response.blob(), `${guide.id}.csv`);
  };

  const notes = takeaways(guide.viz, result);
  const builderQuery = filtersToParams(filters);

  return (
    <div className="guide">
      <nav className="guide__crumbs" aria-label="Breadcrumb">
        <Link href="/explore">← All ready-made charts</Link>
        <span aria-hidden="true">·</span>
        <span>{theme.title}</span>
      </nav>

      <header className="guide__head">
        <h1 className="guide__title">{guide.title}</h1>
        <p className="guide__question">{guide.question}</p>
      </header>

      {(offered.size > 0) && (
        <section className="guide__filters" aria-label="Narrow the chart">
          <span className="guide__filters-title">Narrow it down</span>
          {offered.has('years') && (
            <>
              <label className="guide-filter">
                <span>From</span>
                <Select allowClear placeholder="First year" value={filters.from || undefined} onChange={set('from')} options={yearOptions} style={{ width: 120 }} />
              </label>
              <label className="guide-filter">
                <span>To</span>
                <Select allowClear placeholder="Last year" value={filters.to || undefined} onChange={set('to')} options={yearOptions} style={{ width: 120 }} />
              </label>
            </>
          )}
          {offered.has('type') && (
            <label className="guide-filter">
              <span>Kind of publication</span>
              <Select allowClear showSearch placeholder="All kinds" value={filters.type || undefined} onChange={set('type')} options={options.types.map((t) => ({ value: t, label: t }))} style={{ width: 200 }} />
            </label>
          )}
          {offered.has('school') && (
            <label className="guide-filter">
              <span>School</span>
              <Select allowClear showSearch placeholder="All schools" value={filters.school || undefined} onChange={set('school')} options={options.schools.map((s) => ({ value: s, label: s }))} style={{ width: 260 }} />
            </label>
          )}
          {changed && (
            <Button type="link" onClick={() => setFilters({ ...EMPTY_FILTERS })}>
              Clear filters
            </Button>
          )}
        </section>
      )}

      {backwards && <Alert type="warning" showIcon title="The first year is after the last year" description="Change one of them to see the chart." className="mb-16" />}
      {error && <Alert type="error" showIcon title="The chart could not be drawn" description={error} className="mb-16" />}

      <section className="guide__chart" aria-label={guide.title}>
        <Spin spinning={loading && !backwards}>
          <ChartView viz={guide.viz} result={result} options={chartOptions} height={suggestedHeight(guide.viz, result, chartOptions)} />
        </Spin>
        {result?.truncated && <p className="guide__note">Only the first {result.row_count.toLocaleString('en-GB')} rows are drawn.</p>}
      </section>

      <div className="guide__explain">
        <section aria-labelledby="how-title">
          <h2 id="how-title">How to read this chart</h2>
          <p>{guide.how_to_read}</p>
          {guide.note && <p className="guide__note">{guide.note}</p>}
        </section>
        {notes.length > 0 && (
          <section aria-labelledby="stands-title">
            <h2 id="stands-title">What stands out</h2>
            {notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </section>
        )}
      </div>

      <div className="guide__actions">
        <Tooltip title={canExport ? '' : 'Your role cannot download data'}>
          <Button icon={<DownloadOutlined />} disabled={!result || !canExport} onClick={exportCsv}>
            Download the numbers (CSV)
          </Button>
        </Tooltip>
        <Tooltip title={canSave ? '' : 'Your role cannot save charts'}>
          <Button icon={<SaveOutlined />} disabled={!canSave || !result} onClick={() => setSaveOpen(true)}>
            Save this chart
          </Button>
        </Tooltip>
        {canBuild && (
          <Button icon={<ToolOutlined />} href={`/explore/build?guide=${guide.id}${builderQuery ? `&${builderQuery}` : ''}`}>
            Change it in the chart builder
          </Button>
        )}
      </div>

      <Collapse
        ghost
        className="guide__numbers"
        items={[
          {
            key: 'numbers',
            label: 'See the numbers behind the chart',
            children: <ResultTable result={result} height={320} pageSize={12} />,
          },
        ]}
      />

      {theme.guides.length > 1 && (
        <section className="guide__related" aria-labelledby="related-title">
          <h2 id="related-title">More in {theme.title}</h2>
          <ul>
            {theme.guides
              .filter((other) => other.id !== guide.id)
              .map((other) => (
                <li key={other.id}>
                  <Link href={`/explore/guide/${other.id}`}>{other.title}</Link>
                </li>
              ))}
          </ul>
        </section>
      )}

      <SaveChartModal
        open={saveOpen}
        onClose={() => setSaveOpen(false)}
        name={guide.title}
        description={guide.question}
        getBody={() => ({ viz_type: guide.viz, params: spec, options: guide.options })}
        dashboards={dashboards}
      />
    </div>
  );
}
