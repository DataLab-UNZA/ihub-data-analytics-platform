'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Badge, Button, Dropdown, Empty, Input, InputNumber, Modal, Select, Space, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CodeOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FilterOutlined,
  MoreOutlined,
  PlusOutlined,
  SettingOutlined,
  StarFilled,
  StarOutlined,
} from '@ant-design/icons';
import ChartView from '@/components/charts/ChartView';
import { bff, download } from '@/components/features/explore/client';

const ROW_HEIGHT = 50;

/** The filters a chart receives from the dashboard's filter bar (only columns its dataset has). */
function chartQuery(chart, applied, filterDefs, datasets) {
  const dataset = datasets.find((d) => d.name === chart.dataset);
  const has = (column) => dataset?.columns.some((c) => c.name === column);
  const params = { ...chart.params, filters: [...(chart.params.filters ?? [])] };
  let count = 0;
  for (const def of filterDefs) {
    const value = applied[def.filter_id];
    if (!has(def.column) || value === undefined || value === null) continue;
    if (def.kind === 'year_range') {
      if (value.from) params.year_from = Math.max(params.year_from ?? value.from, value.from);
      if (value.to) params.year_to = Math.min(params.year_to ?? value.to, value.to);
      if (value.from || value.to) count += 1;
    } else if (Array.isArray(value) && value.length) {
      params.filters.push({ column: def.column, op: 'IN', value });
      count += 1;
    }
  }
  return { params, count };
}

function ChartCard({ item, chart, applied, filterDefs, datasets, editing, onChange, onRemove, onMove, canExport }) {
  const { message } = App.useApp();
  const [loaded, setLoaded] = useState({ key: null, result: null, error: null });
  const [sqlOpen, setSqlOpen] = useState(false);
  const { params, count } = useMemo(() => chartQuery(chart, applied, filterDefs, datasets), [chart, applied, filterDefs, datasets]);
  const key = JSON.stringify(params);
  const loading = loaded.key !== key; // still showing the previous query's result
  const { result, error } = loaded;

  useEffect(() => {
    let cancelled = false;
    bff('explore/query', { method: 'POST', body: params })
      .then((data) => !cancelled && setLoaded({ key, result: data, error: null }))
      .catch((err) => !cancelled && setLoaded((prev) => ({ key, result: prev.result, error: err.message })));
    return () => {
      cancelled = true;
    };
  }, [params, key]);

  const exportCsv = async () => {
    const response = await fetch('/bff/explore/query.csv', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) });
    if (!response.ok) return message.error('The CSV could not be created.');
    download(await response.blob(), `${chart.name}.csv`);
  };

  const menu = [
    { key: 'sql', icon: <CodeOutlined />, label: 'View query', onClick: () => setSqlOpen(true) },
    canExport && { key: 'csv', icon: <DownloadOutlined />, label: 'Download as CSV', onClick: exportCsv },
    { key: 'edit', icon: <EditOutlined />, label: <Link href={`/explore?chart=${chart.chart_id}`}>Edit chart</Link> },
  ].filter(Boolean);

  const height = item.height * ROW_HEIGHT;
  return (
    <article className={`dash-card${editing ? ' dash-card--editing' : ''}`} style={{ gridColumn: `span ${item.width}`, height }}>
      <header className="dash-card__head">
        <h2 className="dash-card__title" title={chart.description || chart.name}>
          {chart.name}
        </h2>
        {count > 0 && (
          <Tooltip title={`${count} dashboard filter${count === 1 ? '' : 's'} applied`}>
            <span className="dash-card__filters">
              <FilterOutlined /> <Badge count={count} size="small" color="#2893B3" />
            </span>
          </Tooltip>
        )}
        <Dropdown menu={{ items: menu }} trigger={['click']} placement="bottomRight">
          <Button type="text" size="small" icon={<MoreOutlined />} aria-label={`More for ${chart.name}`} />
        </Dropdown>
      </header>
      {editing && (
        <div className="dash-card__edit">
          <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => onMove(-1)} aria-label="Move left" />
          <Button size="small" icon={<ArrowRightOutlined />} onClick={() => onMove(1)} aria-label="Move right" />
          <Select size="small" value={item.width} onChange={(width) => onChange({ width })} options={[3, 4, 6, 8, 12].map((w) => ({ value: w, label: `${w}/12 wide` }))} />
          <Select size="small" value={item.height} onChange={(h) => onChange({ height: h })} options={[4, 6, 8, 10, 12, 16].map((h) => ({ value: h, label: `${h * ROW_HEIGHT}px tall` }))} />
          <Button size="small" danger icon={<DeleteOutlined />} onClick={onRemove} aria-label="Remove from dashboard" />
        </div>
      )}
      <div className="dash-card__body">
        {error ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error} />
        ) : (
          <Spin spinning={loading}>
            <ChartView viz={chart.viz_type} result={result} options={chart.options} height={height - (editing ? 100 : 64)} />
          </Spin>
        )}
      </div>
      <Modal title={`Query · ${chart.name}`} open={sqlOpen} onCancel={() => setSqlOpen(false)} footer={null} width={720}>
        <pre className="sql-view">{result?.sql}</pre>
      </Modal>
    </article>
  );
}

function FilterControl({ def, value, onChange, datasets }) {
  const [options, setOptions] = useState([]);
  const dataset = datasets.find((d) => d.columns.some((c) => c.name === def.column));
  useEffect(() => {
    if (def.kind !== 'values' || !dataset) return;
    bff(`explore/datasets/${dataset.name}/values/${def.column}`)
      .then((values) => setOptions(values.map((v) => ({ value: v, label: String(v) }))))
      .catch(() => {});
  }, [def, dataset]);
  if (def.kind === 'year_range') {
    return (
      <Space.Compact>
        <InputNumber placeholder="From" min={1800} max={2200} value={value?.from} onChange={(from) => onChange({ ...value, from })} style={{ width: 96 }} />
        <InputNumber placeholder="To" min={1800} max={2200} value={value?.to} onChange={(to) => onChange({ ...value, to })} style={{ width: 96 }} />
      </Space.Compact>
    );
  }
  return (
    <Select
      mode="multiple"
      allowClear
      maxTagCount="responsive"
      placeholder={`${options.length} options`}
      value={value ?? []}
      onChange={onChange}
      options={options}
      style={{ width: 200 }}
    />
  );
}

/** A dashboard in the style of Apache Superset (view and edit). */
export default function DashboardView({ dashboard: initial, charts, datasets, user, startEditing }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [board, setBoard] = useState(initial);
  const [editing, setEditing] = useState(Boolean(startEditing && initial.can_edit));
  const [draft, setDraft] = useState(initial);
  const [pending, setPending] = useState({});
  const [applied, setApplied] = useState({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [newFilter, setNewFilter] = useState({ label: '', column: undefined, kind: 'values' });
  const [saving, setSaving] = useState(false);
  const canExport = user?.permissions?.includes('research:export') ?? false;
  const chartById = useMemo(() => Object.fromEntries(charts.map((c) => [c.chart_id, c])), [charts]);
  const view = editing ? draft : board;

  const filterColumns = useMemo(() => {
    const seen = new Map();
    for (const ds of datasets) for (const c of ds.columns) if (c.groupable && !seen.has(c.name)) seen.set(c.name, c);
    return [...seen.values()];
  }, [datasets]);

  const toggleFavourite = async () => {
    try {
      setBoard(await bff(`dashboards/${board.dashboard_id}/favourite`, { method: 'PUT', body: { favourite: !board.favourite } }));
    } catch (err) {
      message.error(err.message);
    }
  };

  const patch = useCallback(
    async (body) => {
      const updated = await bff(`dashboards/${board.dashboard_id}`, { method: 'PATCH', body });
      setBoard(updated);
      setDraft(updated);
      return updated;
    },
    [board.dashboard_id],
  );

  const save = async () => {
    setSaving(true);
    try {
      await patch({ title: draft.title, items: draft.items, filters: draft.filters });
      setEditing(false);
      message.success('Dashboard saved.');
      router.replace(`/dashboards/${board.dashboard_id}`);
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const togglePublished = async () => {
    try {
      const updated = await patch({ published: !board.published });
      message.success(updated.published ? 'Published: everyone who can read research sees it.' : 'Back to draft.');
    } catch (err) {
      message.error(err.message);
    }
  };

  const setItem = (index, changes) => setDraft((d) => ({ ...d, items: d.items.map((it, i) => (i === index ? { ...it, ...changes } : it)) }));
  const moveItem = (index, step) =>
    setDraft((d) => {
      const items = [...d.items];
      const target = index + step;
      if (target < 0 || target >= items.length) return d;
      [items[index], items[target]] = [items[target], items[index]];
      return { ...d, items };
    });

  const addFilter = () => {
    if (!newFilter.column) return;
    const column = filterColumns.find((c) => c.name === newFilter.column);
    const def = {
      filter_id: crypto.randomUUID().slice(0, 8),
      label: newFilter.label || column.label,
      column: newFilter.column,
      kind: column.type === 'year' ? 'year_range' : 'values',
    };
    setDraft((d) => ({ ...d, filters: [...d.filters, def] }));
    setNewFilter({ label: '', column: undefined, kind: 'values' });
  };

  const missing = view.items.filter((item) => !chartById[item.chart_id]);
  const available = charts.filter((c) => !draft.items.some((item) => item.chart_id === c.chart_id));

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        {editing ? (
          <Input className="dashboard__title-input" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} maxLength={120} />
        ) : (
          <Typography.Title level={3} className="dashboard__title">
            {board.title}
          </Typography.Title>
        )}
        <Button type="text" onClick={toggleFavourite} aria-label={board.favourite ? 'Remove from favourites' : 'Add to favourites'} icon={board.favourite ? <StarFilled className="star--on" /> : <StarOutlined />} />
        {board.can_edit ? (
          <Tooltip title={board.published ? 'Click to make it a draft' : 'Click to publish'}>
            <Tag className="dashboard__status" color={board.published ? 'green' : undefined} onClick={togglePublished}>
              {board.published ? 'Published' : 'Draft'}
            </Tag>
          </Tooltip>
        ) : (
          <Tag color={board.published ? 'green' : undefined}>{board.published ? 'Published' : 'Draft'}</Tag>
        )}
        <div className="dashboard__actions">
          {editing ? (
            <>
              <Button onClick={() => (setDraft(board), setEditing(false))}>DISCARD</Button>
              <Button type="primary" loading={saving} onClick={save}>
                SAVE
              </Button>
            </>
          ) : (
            board.can_edit && (
              <Button type="primary" ghost onClick={() => setEditing(true)}>
                EDIT DASHBOARD
              </Button>
            )
          )}
        </div>
      </header>

      <div className="filter-bar" role="search" aria-label="Dashboard filters">
        <SettingOutlined className="filter-bar__gear" />
        {editing && (
          <Button type="link" icon={<PlusOutlined />} onClick={() => setFiltersOpen(true)}>
            ADD/EDIT FILTERS
          </Button>
        )}
        {view.filters.length === 0 && !editing && <span className="filter-bar__empty">No filters on this dashboard</span>}
        {view.filters.map((def) => (
          <label key={def.filter_id} className="filter-bar__item">
            <span>{def.label}</span>
            <FilterControl def={def} value={pending[def.filter_id]} onChange={(value) => setPending({ ...pending, [def.filter_id]: value })} datasets={datasets} />
          </label>
        ))}
        {view.filters.length > 0 && (
          <div className="filter-bar__apply">
            <Button type="primary" disabled={JSON.stringify(pending) === JSON.stringify(applied)} onClick={() => setApplied(pending)}>
              APPLY
            </Button>
            <Button type="link" onClick={() => (setPending({}), setApplied({}))}>
              Clear All
            </Button>
          </div>
        )}
      </div>

      {editing && (
        <div className="dashboard__add">
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={available.length ? 'Add a saved chart to this dashboard' : 'Every saved chart is on this dashboard'}
            disabled={!available.length}
            value={null}
            onChange={(chartId) => setDraft((d) => ({ ...d, items: [...d.items, { chart_id: chartId, width: 6, height: 8 }] }))}
            options={available.map((c) => ({ value: c.chart_id, label: c.name }))}
            style={{ width: 360 }}
          />
          <Link href="/explore">
            <Button icon={<PlusOutlined />}>New chart in Explore</Button>
          </Link>
        </div>
      )}

      {view.items.length === 0 ? (
        <div className="dashboard__empty">
          <Empty description={board.can_edit ? 'This dashboard has no charts yet. Edit it to add saved charts.' : 'This dashboard has no charts yet.'} />
        </div>
      ) : (
        <div className="dashboard__grid">
          {view.items.map((item, index) =>
            chartById[item.chart_id] ? (
              <ChartCard
                key={`${item.chart_id}-${index}`}
                item={item}
                chart={chartById[item.chart_id]}
                applied={applied}
                filterDefs={view.filters}
                datasets={datasets}
                editing={editing}
                canExport={canExport}
                onChange={(changes) => setItem(index, changes)}
                onRemove={() => setDraft((d) => ({ ...d, items: d.items.filter((_, i) => i !== index) }))}
                onMove={(step) => moveItem(index, step)}
              />
            ) : null,
          )}
        </div>
      )}
      {missing.length > 0 && <p className="control-hint">{missing.length} chart(s) on this dashboard were deleted.</p>}

      <Modal title="Dashboard filters" open={filtersOpen} onCancel={() => setFiltersOpen(false)} onOk={() => setFiltersOpen(false)} okText="Done">
        <p className="control-hint mb-16">A filter applies to every chart whose dataset has the column. Save the dashboard to keep the filters.</p>
        {draft.filters.map((def) => (
          <div key={def.filter_id} className="switch-row">
            <span>
              {def.label} <small className="text-muted">({def.kind === 'year_range' ? 'year range' : 'values'})</small>
            </span>
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => setDraft((d) => ({ ...d, filters: d.filters.filter((f) => f.filter_id !== def.filter_id) }))} aria-label={`Remove ${def.label}`} />
          </div>
        ))}
        <Space.Compact className="w-full mt-12">
          <Select
            className="w-full"
            placeholder="Column"
            value={newFilter.column}
            onChange={(column) => setNewFilter({ ...newFilter, column })}
            options={filterColumns.map((c) => ({ value: c.name, label: c.label }))}
            showSearch
            optionFilterProp="label"
          />
          <Input placeholder="Label (optional)" value={newFilter.label} onChange={(e) => setNewFilter({ ...newFilter, label: e.target.value })} />
          <Button type="primary" icon={<PlusOutlined />} disabled={!newFilter.column} onClick={addFilter}>
            Add
          </Button>
        </Space.Compact>
      </Modal>
    </div>
  );
}
