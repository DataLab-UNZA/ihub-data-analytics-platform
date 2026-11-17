'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Alert,
  App,
  Button,
  Checkbox,
  Collapse,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  AppstoreOutlined,
  AreaChartOutlined,
  BarChartOutlined,
  CheckSquareOutlined,
  CloseOutlined,
  CodeOutlined,
  FieldTimeOutlined,
  FileTextOutlined,
  FunctionOutlined,
  GlobalOutlined,
  HeatMapOutlined,
  LineChartOutlined,
  NumberOutlined,
  PieChartOutlined,
  PlusOutlined,
  SaveOutlined,
  SearchOutlined,
  TableOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import ChartView, { ResultTable } from '@/components/charts/ChartView';
import { DEFAULT_OPTIONS, VIZ_TYPES } from '@/lib/viz';
import { bff, download, formFromParams, metricKey, querySpec } from './client';

const VIZ_ICONS = {
  table: <TableOutlined />,
  big_number: <NumberOutlined />,
  bar: <BarChartOutlined />,
  line: <LineChartOutlined />,
  area: <AreaChartOutlined />,
  pie: <PieChartOutlined />,
  treemap: <AppstoreOutlined />,
  heatmap: <HeatMapOutlined />,
  world_map: <GlobalOutlined />,
};
const TYPE_ICONS = { string: 'ABC', number: '#', year: <FieldTimeOutlined />, boolean: <CheckSquareOutlined /> };
const OPERATORS = [
  ['==', 'equals'],
  ['!=', 'not equal'],
  ['IN', 'in'],
  ['NOT IN', 'not in'],
  ['>', '>'],
  ['<', '<'],
  ['>=', '≥'],
  ['<=', '≤'],
  ['CONTAINS', 'contains'],
  ['IS NULL', 'is empty'],
  ['IS NOT NULL', 'is not empty'],
];
const AGGREGATES = ['COUNT', 'COUNT_DISTINCT', 'SUM', 'AVG', 'MIN', 'MAX'];

const DEFAULT_FORM = {
  dataset: 'publications',
  viz: 'bar',
  metrics: ['count'],
  groupby: ['year'],
  filters: [],
  yearFrom: null,
  yearTo: null,
  seriesLimit: null,
  orderDesc: true,
  rowLimit: 1000,
  options: {},
};

function Section({ title, children, extra }) {
  return (
    <section className="explore-section">
      <header className="explore-section__head">
        <h3>{title}</h3>
        {extra}
      </header>
      <div className="explore-section__body">{children}</div>
    </section>
  );
}

function ControlLabel({ children, action }) {
  return (
    <div className="control-label">
      <span>{children}</span>
      {action}
    </div>
  );
}

/** One filter row: column, operator and value(s) with suggestions from the data. */
function FilterRow({ filter, dataset, onChange, onRemove }) {
  const column = dataset.columns.find((c) => c.name === filter.column);
  const [options, setOptions] = useState([]);
  const multi = filter.op === 'IN' || filter.op === 'NOT IN';
  const noValue = filter.op === 'IS NULL' || filter.op === 'IS NOT NULL';

  useEffect(() => {
    if (!column || column.type === 'number') return;
    let cancelled = false;
    bff(`explore/datasets/${dataset.name}/values/${column.name}`)
      .then((values) => !cancelled && setOptions(values.map((v) => ({ value: v, label: String(v) }))))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [dataset.name, column]);

  let valueInput = null;
  if (!noValue && column) {
    if ((column.type === 'number' || column.type === 'year') && !multi) {
      valueInput = <InputNumber className="w-full" value={filter.value} onChange={(value) => onChange({ value })} placeholder="Value" />;
    } else if (filter.op === 'CONTAINS') {
      valueInput = <Input value={filter.value} onChange={(e) => onChange({ value: e.target.value })} placeholder="Text" />;
    } else {
      valueInput = (
        <Select
          className="w-full"
          mode={multi ? 'multiple' : undefined}
          showSearch
          allowClear
          value={filter.value}
          options={options}
          onChange={(value) => onChange({ value })}
          placeholder={multi ? 'Values' : 'Value'}
          maxTagCount="responsive"
        />
      );
    }
  }

  return (
    <div className="filter-row">
      <Select
        className="filter-row__column"
        value={filter.column}
        placeholder="Column"
        options={dataset.columns.map((c) => ({ value: c.name, label: c.label }))}
        onChange={(value) => onChange({ column: value, value: undefined })}
        showSearch
        optionFilterProp="label"
      />
      <Select
        className="filter-row__op"
        value={filter.op}
        options={OPERATORS.map(([value, label]) => ({ value, label }))}
        onChange={(op) => onChange({ op, value: op === 'IN' || op === 'NOT IN' ? [] : undefined })}
      />
      <div className="filter-row__value">{valueInput}</div>
      <Button type="text" size="small" icon={<CloseOutlined />} onClick={onRemove} aria-label="Remove filter" />
    </div>
  );
}

/** Adds a simple ad-hoc metric (aggregate of a column), like Superset's metric popover. */
function AdhocMetric({ dataset, onAdd }) {
  const [aggregate, setAggregate] = useState('SUM');
  const [column, setColumn] = useState();
  const numeric = aggregate === 'SUM' || aggregate === 'AVG';
  const columns = dataset.columns.filter((c) => !numeric || c.type === 'number');
  return (
    <Space.Compact className="w-full">
      <Select value={aggregate} onChange={setAggregate} options={AGGREGATES.map((a) => ({ value: a, label: a }))} style={{ width: 150 }} />
      <Select value={column} onChange={setColumn} placeholder="Column" options={columns.map((c) => ({ value: c.name, label: c.label }))} className="w-full" />
      <Button disabled={!column} onClick={() => column && onAdd({ aggregate, column })} icon={<PlusOutlined />} />
    </Space.Compact>
  );
}

export default function ExploreView({ datasets, chart, user, dashboards }) {
  const router = useRouter();
  const { message } = App.useApp();
  const initial = chart ? formFromParams(chart.params, chart.viz_type, chart.options) : DEFAULT_FORM;
  const [form, setForm] = useState(initial);
  const [name, setName] = useState(chart?.name ?? 'Untitled chart');
  const [result, setResult] = useState(null);
  const [ranSpec, setRanSpec] = useState(null);
  const [samples, setSamples] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [rowSearch, setRowSearch] = useState('');
  const [gallery, setGallery] = useState(false);
  const [showSql, setShowSql] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveForm, setSaveForm] = useState({ name: chart?.name ?? '', description: chart?.description ?? '', dashboard: null, asNew: false });
  const [dataTab, setDataTab] = useState('results');
  const ran = useRef(false);

  const dataset = datasets.find((d) => d.name === form.dataset) ?? datasets[0];
  const spec = useMemo(() => querySpec(form), [form]);
  const altered = ranSpec !== null && JSON.stringify(spec) !== JSON.stringify(ranSpec);
  const options = { ...DEFAULT_OPTIONS, ...form.options };
  const canSave = user?.permissions?.includes('reports:manage') ?? false;
  const canExport = user?.permissions?.includes('research:export') ?? false;
  const canEdit = !chart || chart.can_edit;

  const update = (changes) => setForm((current) => ({ ...current, ...changes }));
  const setOption = (key, value) => setForm((current) => ({ ...current, options: { ...current.options, [key]: value } }));

  const run = useCallback(async () => {
    const body = querySpec(form);
    setLoading(true);
    setError(null);
    try {
      const data = await bff('explore/query', { method: 'POST', body });
      setResult(data);
      setRanSpec(body);
      setSamples(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    if (!ran.current) {
      ran.current = true;
      run();
    }
  }, [run]);

  const loadSamples = async () => {
    setDataTab('samples');
    if (samples) return;
    try {
      setSamples(await bff('explore/samples', { method: 'POST', body: spec }));
    } catch (err) {
      message.error(err.message);
    }
  };

  const changeDataset = (value) => {
    const next = datasets.find((d) => d.name === value);
    update({ dataset: value, metrics: [next.metrics[0].name], groupby: [next.time_column], filters: [] });
  };

  const exportCsv = async () => {
    const response = await fetch('/bff/explore/query.csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    });
    if (!response.ok) {
      message.error('The CSV could not be created.');
      return;
    }
    download(await response.blob(), `${name || 'chart'}.csv`);
  };

  const save = async () => {
    setSaving(true);
    try {
      const body = { name: saveForm.name || name, description: saveForm.description, viz_type: form.viz, params: spec, options: form.options };
      const saved = chart && canEdit && !saveForm.asNew
        ? await bff(`charts/${chart.chart_id}`, { method: 'PATCH', body })
        : await bff('charts', { method: 'POST', body });
      if (saveForm.dashboard) {
        const board = await bff(`dashboards/${saveForm.dashboard}`);
        if (!board.items.some((item) => item.chart_id === saved.chart_id)) {
          await bff(`dashboards/${saveForm.dashboard}`, {
            method: 'PATCH',
            body: { items: [...board.items, { chart_id: saved.chart_id, width: 6, height: 8 }] },
          });
        }
      }
      message.success(saveForm.dashboard ? 'Chart saved and added to the dashboard.' : 'Chart saved.');
      setSaveOpen(false);
      setName(saved.name);
      router.replace(`/explore?chart=${saved.chart_id}`);
      router.refresh();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const term = search.trim().toLowerCase();
  const metricsShown = dataset.metrics.filter((m) => !term || m.label.toLowerCase().includes(term));
  const columnsShown = dataset.columns.filter((c) => !term || c.label.toLowerCase().includes(term));
  const metricLabel = (m) =>
    typeof m === 'string'
      ? (dataset.metrics.find((x) => x.name === m)?.label ?? m)
      : `${m.aggregate}(${dataset.columns.find((c) => c.name === m.column)?.label ?? m.column})`;

  const filteredRows = (data) => {
    if (!data || !rowSearch.trim()) return data;
    const needle = rowSearch.trim().toLowerCase();
    return { ...data, rows: data.rows.filter((row) => row.some((v) => String(v ?? '').toLowerCase().includes(needle))) };
  };

  const vizMeta = VIZ_TYPES.find((v) => v.key === form.viz);

  return (
    <div className="explore">
      {/* Dataset panel */}
      <aside className="explore__datasource" aria-label="Dataset">
        <p className="explore__panel-title">Dataset</p>
        <Select
          className="w-full"
          value={form.dataset}
          onChange={changeDataset}
          options={datasets.map((d) => ({ value: d.name, label: d.label }))}
          suffixIcon={<TableOutlined />}
        />
        <p className="explore__dataset-help">{dataset.description}</p>
        <Input allowClear prefix={<SearchOutlined />} placeholder="Search metrics & columns" value={search} onChange={(e) => setSearch(e.target.value)} />
        <Collapse
          ghost
          defaultActiveKey={['metrics', 'columns']}
          className="explore__fields"
          items={[
            {
              key: 'metrics',
              label: (
                <span>
                  Metrics <small>Showing {metricsShown.length} of {dataset.metrics.length}</small>
                </span>
              ),
              children: (
                <ul className="field-list">
                  {metricsShown.map((m) => (
                    <li key={m.name}>
                      <button type="button" onClick={() => !form.metrics.includes(m.name) && update({ metrics: [...form.metrics, m.name] })} title={m.description || `Add ${m.label}`}>
                        <span className="field-list__icon">
                          <FunctionOutlined />
                        </span>
                        {m.label}
                      </button>
                    </li>
                  ))}
                </ul>
              ),
            },
            {
              key: 'columns',
              label: (
                <span>
                  Columns <small>Showing {columnsShown.length} of {dataset.columns.length}</small>
                </span>
              ),
              children: (
                <ul className="field-list">
                  {columnsShown.map((c) => (
                    <li key={c.name}>
                      <button
                        type="button"
                        disabled={!c.groupable}
                        onClick={() => c.groupable && !form.groupby.includes(c.name) && update({ groupby: [...form.groupby, c.name] })}
                        title={c.groupable ? `Group by ${c.label}` : `${c.label} (filter only)`}
                      >
                        <span className="field-list__icon">{TYPE_ICONS[c.type]}</span>
                        {c.label}
                      </button>
                    </li>
                  ))}
                </ul>
              ),
            },
          ]}
        />
      </aside>

      {/* Control panel */}
      <section className="explore__controls" aria-label="Chart controls">
        <div className="explore__actions">
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={run} loading={loading} block>
            RUN
          </Button>
          <Tooltip title={canSave ? '' : 'Your role cannot save charts'}>
            <Button icon={<SaveOutlined />} disabled={!canSave} onClick={() => setSaveOpen(true)} block>
              SAVE
            </Button>
          </Tooltip>
        </div>
        <Tabs
          className="explore__tabs"
          centered
          items={[
            {
              key: 'data',
              label: 'DATA',
              children: (
                <div className="explore__control-scroll">
                  <Section title="Chart Type">
                    <ControlLabel>VISUALIZATION TYPE</ControlLabel>
                    <button type="button" className="viz-picker" onClick={() => setGallery(true)}>
                      {VIZ_ICONS[form.viz]} {vizMeta?.label}
                      <span className="viz-picker__more">View all charts</span>
                    </button>
                  </Section>
                  <Section title="Time">
                    <ControlLabel>YEAR RANGE</ControlLabel>
                    <Space.Compact className="w-full">
                      <InputNumber className="w-full" placeholder="From" min={1800} max={2200} value={form.yearFrom} onChange={(v) => update({ yearFrom: v })} />
                      <InputNumber className="w-full" placeholder="To" min={1800} max={2200} value={form.yearTo} onChange={(v) => update({ yearTo: v })} />
                    </Space.Compact>
                    <p className="control-hint">{form.yearFrom || form.yearTo ? `${form.yearFrom ?? '-∞'} ≤ year ≤ ${form.yearTo ?? '∞'}` : 'No filter: every year'}</p>
                  </Section>
                  <Section title="Query">
                    <ControlLabel>METRICS</ControlLabel>
                    <Select
                      className="w-full"
                      mode="multiple"
                      value={form.metrics.map(metricKey)}
                      options={[
                        ...dataset.metrics.map((m) => ({ value: m.name, label: m.label })),
                        ...form.metrics.filter((m) => typeof m !== 'string').map((m) => ({ value: metricKey(m), label: metricLabel(m) })),
                      ]}
                      onChange={(keys) => update({ metrics: form.metrics.filter((m) => keys.includes(metricKey(m))).concat(keys.filter((k) => !form.metrics.some((m) => metricKey(m) === k))) })}
                      placeholder="Add metric"
                    />
                    <div className="mt-8">
                      <AdhocMetric dataset={dataset} onAdd={(m) => !form.metrics.some((x) => metricKey(x) === metricKey(m)) && update({ metrics: [...form.metrics, m] })} />
                    </div>

                    <ControlLabel
                      action={
                        <Button size="small" type="text" icon={<PlusOutlined />} onClick={() => update({ filters: [...form.filters, { id: crypto.randomUUID(), column: undefined, op: '==', value: undefined }] })} aria-label="Add filter" />
                      }
                    >
                      FILTERS
                    </ControlLabel>
                    {form.filters.length === 0 && (
                      <button type="button" className="dashed-add" onClick={() => update({ filters: [{ id: crypto.randomUUID(), column: undefined, op: '==', value: undefined }] })}>
                        <PlusOutlined /> Add filter
                      </button>
                    )}
                    {form.filters.map((filter) => (
                      <FilterRow
                        key={filter.id}
                        filter={filter}
                        dataset={dataset}
                        onChange={(changes) => update({ filters: form.filters.map((f) => (f.id === filter.id ? { ...f, ...changes } : f)) })}
                        onRemove={() => update({ filters: form.filters.filter((f) => f.id !== filter.id) })}
                      />
                    ))}

                    <ControlLabel>GROUP BY</ControlLabel>
                    <Select
                      className="w-full"
                      mode="multiple"
                      value={form.groupby}
                      options={dataset.columns.filter((c) => c.groupable).map((c) => ({ value: c.name, label: c.label }))}
                      onChange={(groupby) => update({ groupby })}
                      placeholder="Drop columns here or click"
                      maxCount={5}
                    />
                    <p className="control-hint">{dataset.columns.filter((c) => c.groupable).length} option(s)</p>

                    <div className="control-grid">
                      <div>
                        <ControlLabel>SERIES LIMIT</ControlLabel>
                        <InputNumber className="w-full" min={1} max={100} value={form.seriesLimit} onChange={(v) => update({ seriesLimit: v })} placeholder="None" />
                      </div>
                      <div>
                        <ControlLabel>ROW LIMIT</ControlLabel>
                        <Select className="w-full" value={form.rowLimit} onChange={(v) => update({ rowLimit: v })} options={[10, 50, 100, 1000, 5000, 10000].map((v) => ({ value: v, label: v.toLocaleString('en-GB') }))} />
                      </div>
                    </div>
                    <Checkbox className="mt-12" checked={form.orderDesc} onChange={(e) => update({ orderDesc: e.target.checked })}>
                      SORT DESCENDING
                    </Checkbox>
                  </Section>
                </div>
              ),
            },
            {
              key: 'customize',
              label: 'CUSTOMIZE',
              children: (
                <div className="explore__control-scroll">
                  <Section title="Chart Options">
                    <div className="switch-row">
                      <span>Legend</span>
                      <Switch size="small" checked={options.show_legend} onChange={(v) => setOption('show_legend', v)} />
                    </div>
                    <div className="switch-row">
                      <span>Show values</span>
                      <Switch size="small" checked={options.show_values} onChange={(v) => setOption('show_values', v)} />
                    </div>
                    {['bar', 'area', 'line'].includes(form.viz) && (
                      <div className="switch-row">
                        <span>Stacked</span>
                        <Switch size="small" checked={options.stacked} onChange={(v) => setOption('stacked', v)} />
                      </div>
                    )}
                    {form.viz === 'bar' && (
                      <div className="switch-row">
                        <span>Horizontal bars</span>
                        <Switch size="small" checked={options.horizontal} onChange={(v) => setOption('horizontal', v)} />
                      </div>
                    )}
                    {form.viz === 'pie' && (
                      <div className="switch-row">
                        <span>Donut</span>
                        <Switch size="small" checked={options.donut} onChange={(v) => setOption('donut', v)} />
                      </div>
                    )}
                  </Section>
                  {['bar', 'line', 'area'].includes(form.viz) && (
                    <Section title="Axes">
                      <ControlLabel>X AXIS TITLE</ControlLabel>
                      <Input value={options.x_label} onChange={(e) => setOption('x_label', e.target.value)} placeholder="From the group-by column" />
                      <ControlLabel>Y AXIS TITLE</ControlLabel>
                      <Input value={options.y_label} onChange={(e) => setOption('y_label', e.target.value)} placeholder="From the metric" />
                    </Section>
                  )}
                  {form.viz === 'big_number' && (
                    <Section title="Big Number">
                      <ControlLabel>SUBHEADER</ControlLabel>
                      <Input value={options.subheader} onChange={(e) => setOption('subheader', e.target.value)} placeholder="From the metric" />
                    </Section>
                  )}
                </div>
              ),
            },
          ]}
        />
      </section>

      {/* Chart and data */}
      <section className="explore__main" aria-label="Chart">
        <header className="explore__header">
          <Typography.Title level={3} className="explore__title" editable={canEdit ? { onChange: setName, triggerType: ['text', 'icon'] } : false}>
            {name}
          </Typography.Title>
          {altered && <Tag color="gold">Altered</Tag>}
          <div className="explore__meta">
            {result && <Tag className="pill">{result.row_count.toLocaleString('en-GB')} rows</Tag>}
            {result && <Tag className="pill pill--success">{(result.duration_ms / 1000).toFixed(2)}s</Tag>}
            <Space.Compact>
              <Tooltip title="View query">
                <Button icon={<CodeOutlined />} onClick={() => setShowSql(true)} disabled={!result} />
              </Tooltip>
              <Button icon={<FileTextOutlined />} disabled={!result} onClick={() => download(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }), `${name}.json`)}>
                .JSON
              </Button>
              <Tooltip title={canExport ? '' : 'Your role cannot export data'}>
                <Button icon={<FileTextOutlined />} disabled={!result || !canExport} onClick={exportCsv}>
                  .CSV
                </Button>
              </Tooltip>
            </Space.Compact>
          </div>
        </header>

        {error && <Alert type="error" showIcon title="The query failed" description={error} closable onClose={() => setError(null)} className="mb-16" />}

        <div className={`explore__chart${altered ? ' explore__chart--stale' : ''}`}>
          <Spin spinning={loading}>
            <ChartView viz={form.viz} result={result} options={options} height={420} />
          </Spin>
          {altered && !loading && (
            <Button type="primary" className="explore__run-overlay" onClick={run}>
              RUN QUERY
            </Button>
          )}
        </div>

        <Collapse
          className="explore__data"
          defaultActiveKey={['data']}
          items={[
            {
              key: 'data',
              label: 'Data',
              children: (
                <Tabs
                  activeKey={dataTab}
                  onChange={(key) => (key === 'samples' ? loadSamples() : setDataTab(key))}
                  tabBarExtraContent={
                    <Space>
                      {(dataTab === 'results' ? result : samples) && (
                        <Tag className="pill">{(dataTab === 'results' ? result : samples).row_count} rows retrieved</Tag>
                      )}
                      <Input size="small" allowClear prefix={<SearchOutlined />} placeholder="Search" value={rowSearch} onChange={(e) => setRowSearch(e.target.value)} />
                    </Space>
                  }
                  items={[
                    { key: 'results', label: 'VIEW RESULTS', children: <ResultTable result={filteredRows(result)} height={280} pageSize={10} /> },
                    { key: 'samples', label: 'VIEW SAMPLES', children: samples ? <ResultTable result={filteredRows(samples)} height={280} pageSize={10} /> : <Spin /> },
                  ]}
                />
              ),
            },
          ]}
        />
      </section>

      <Modal title="Choose a visualization type" open={gallery} onCancel={() => setGallery(false)} footer={null} width={760}>
        <div className="viz-gallery">
          {VIZ_TYPES.map((v) => (
            <button
              key={v.key}
              type="button"
              className={`viz-gallery__item${v.key === form.viz ? ' viz-gallery__item--active' : ''}`}
              onClick={() => {
                update({ viz: v.key });
                setGallery(false);
              }}
            >
              <span className="viz-gallery__icon">{VIZ_ICONS[v.key]}</span>
              <strong>{v.label}</strong>
              <small>{v.hint}</small>
            </button>
          ))}
        </div>
      </Modal>

      <Modal title="Query" open={showSql} onCancel={() => setShowSql(false)} footer={null} width={720}>
        <pre className="sql-view">{result?.sql}</pre>
        <p className="control-hint">Parameters: {JSON.stringify(result?.params ?? [])}</p>
      </Modal>

      <Modal
        title={chart ? 'Save chart' : 'Save new chart'}
        open={saveOpen}
        onCancel={() => setSaveOpen(false)}
        onOk={save}
        okText="Save"
        confirmLoading={saving}
      >
        <div className="stack stack--sm">
          {chart && canEdit && (
            <Checkbox checked={saveForm.asNew} onChange={(e) => setSaveForm({ ...saveForm, asNew: e.target.checked })}>
              Save as a new chart
            </Checkbox>
          )}
          <ControlLabel>CHART NAME</ControlLabel>
          <Input value={saveForm.name || name} onChange={(e) => setSaveForm({ ...saveForm, name: e.target.value })} maxLength={120} />
          <ControlLabel>DESCRIPTION</ControlLabel>
          <Input.TextArea value={saveForm.description} onChange={(e) => setSaveForm({ ...saveForm, description: e.target.value })} maxLength={500} rows={2} />
          <ControlLabel>ADD TO DASHBOARD</ControlLabel>
          <Select
            className="w-full"
            allowClear
            placeholder="Optional"
            value={saveForm.dashboard}
            onChange={(dashboard) => setSaveForm({ ...saveForm, dashboard })}
            options={dashboards.filter((d) => d.can_edit).map((d) => ({ value: d.dashboard_id, label: d.title }))}
          />
        </div>
      </Modal>
    </div>
  );
}
