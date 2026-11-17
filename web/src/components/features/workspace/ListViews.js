'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { App, Button, Input, Modal, Popconfirm, Table, Tag, Tooltip } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined, StarFilled, StarOutlined } from '@ant-design/icons';
import { VIZ_TYPES } from '@/lib/viz';
import { bff } from '@/components/features/explore/client';

const DATE = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
const vizLabel = (key) => VIZ_TYPES.find((v) => v.key === key)?.label ?? key;

function ListHeader({ title, count, action, search, onSearch }) {
  return (
    <div className="list-view__head">
      <h1 className="list-view__title">
        {title} <span className="list-view__count">{count}</span>
      </h1>
      <Input className="list-view__search" allowClear prefix={<SearchOutlined />} placeholder={`Search ${title.toLowerCase()}`} value={search} onChange={(e) => onSearch(e.target.value)} />
      {action}
    </div>
  );
}

/** Saved charts, like Superset's chart list. */
export function ChartList({ charts, datasets, canCreate }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [search, setSearch] = useState('');
  const datasetLabel = (name) => datasets.find((d) => d.name === name)?.label ?? name;
  const shown = charts.filter((c) => !search || `${c.name} ${c.description}`.toLowerCase().includes(search.toLowerCase()));

  const remove = async (chart) => {
    try {
      await bff(`charts/${chart.chart_id}`, { method: 'DELETE' });
      message.success(`Deleted “${chart.name}”.`);
      router.refresh();
    } catch (err) {
      message.error(err.message);
    }
  };

  return (
    <section className="list-view">
      <ListHeader
        title="Charts"
        count={charts.length}
        search={search}
        onSearch={setSearch}
        action={
          canCreate && (
            <Link href="/explore">
              <Button type="primary" icon={<PlusOutlined />}>
                CHART
              </Button>
            </Link>
          )
        }
      />
      <Table
        rowKey="chart_id"
        dataSource={shown}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        locale={{ emptyText: canCreate ? 'No charts yet. Build one in Explore and save it.' : 'No charts yet.' }}
        columns={[
          {
            title: 'Name',
            dataIndex: 'name',
            sorter: (a, b) => a.name.localeCompare(b.name),
            render: (name, chart) => (
              <span>
                <Link href={`/explore?chart=${chart.chart_id}`}>{name}</Link>
                {chart.description && <small className="list-view__desc">{chart.description}</small>}
              </span>
            ),
          },
          { title: 'Visualization type', dataIndex: 'viz_type', render: (v) => <Tag>{vizLabel(v)}</Tag>, filters: VIZ_TYPES.map((v) => ({ text: v.label, value: v.key })), onFilter: (value, chart) => chart.viz_type === value },
          { title: 'Dataset', dataIndex: 'dataset', render: datasetLabel },
          { title: 'Last modified', dataIndex: 'updated_at', sorter: (a, b) => a.updated_at.localeCompare(b.updated_at), defaultSortOrder: 'descend', render: (v) => DATE.format(new Date(v)) },
          {
            title: 'Actions',
            key: 'actions',
            width: 110,
            render: (_, chart) => (
              <span className="list-view__actions">
                <Tooltip title="Edit in Explore">
                  <Link href={`/explore?chart=${chart.chart_id}`} aria-label={`Edit ${chart.name}`}>
                    <EditOutlined />
                  </Link>
                </Tooltip>
                {chart.can_edit && (
                  <Popconfirm title="Delete this chart?" description="It is also removed from every dashboard." okText="Delete" okButtonProps={{ danger: true }} onConfirm={() => remove(chart)}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} aria-label={`Delete ${chart.name}`} />
                  </Popconfirm>
                )}
              </span>
            ),
          },
        ]}
      />
    </section>
  );
}

/** Dashboards, like Superset's dashboard list: favourites, status and a "+ Dashboard" button. */
export function DashboardList({ dashboards, canCreate, startNew }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [search, setSearch] = useState('');
  const rows = dashboards; // fresh from the server; router.refresh() reloads after changes
  const [creating, setCreating] = useState(Boolean(startNew && canCreate));
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const shown = rows.filter((d) => !search || d.title.toLowerCase().includes(search.toLowerCase()));

  const toggleFavourite = async (board) => {
    try {
      await bff(`dashboards/${board.dashboard_id}/favourite`, { method: 'PUT', body: { favourite: !board.favourite } });
      router.refresh();
    } catch (err) {
      message.error(err.message);
    }
  };

  const create = async () => {
    setBusy(true);
    try {
      const board = await bff('dashboards', { method: 'POST', body: { title } });
      router.push(`/dashboards/${board.dashboard_id}?edit=1`);
    } catch (err) {
      message.error(err.message);
      setBusy(false);
    }
  };

  const remove = async (board) => {
    try {
      await bff(`dashboards/${board.dashboard_id}`, { method: 'DELETE' });
      router.refresh();
      message.success(`Deleted “${board.title}”.`);
    } catch (err) {
      message.error(err.message);
    }
  };

  return (
    <section className="list-view">
      <ListHeader
        title="Dashboards"
        count={rows.length}
        search={search}
        onSearch={setSearch}
        action={
          canCreate && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
              DASHBOARD
            </Button>
          )
        }
      />
      <Table
        rowKey="dashboard_id"
        dataSource={shown}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        locale={{ emptyText: canCreate ? 'No dashboards yet. Create one with + DASHBOARD.' : 'No published dashboards yet.' }}
        columns={[
          {
            key: 'fav',
            width: 44,
            render: (_, board) => (
              <Button type="text" size="small" onClick={() => toggleFavourite(board)} aria-label={board.favourite ? 'Remove from favourites' : 'Add to favourites'} icon={board.favourite ? <StarFilled className="star--on" /> : <StarOutlined />} />
            ),
          },
          { title: 'Name', dataIndex: 'title', sorter: (a, b) => a.title.localeCompare(b.title), render: (t, board) => <Link href={`/dashboards/${board.dashboard_id}`}>{t}</Link> },
          { title: 'Status', dataIndex: 'published', render: (p) => <Tag color={p ? 'green' : undefined}>{p ? 'Published' : 'Draft'}</Tag> },
          { title: 'Charts', key: 'charts', render: (_, board) => board.items.length },
          { title: 'Last modified', dataIndex: 'updated_at', sorter: (a, b) => a.updated_at.localeCompare(b.updated_at), defaultSortOrder: 'descend', render: (v) => DATE.format(new Date(v)) },
          {
            title: 'Actions',
            key: 'actions',
            width: 110,
            render: (_, board) =>
              board.can_edit && (
                <span className="list-view__actions">
                  <Tooltip title="Edit">
                    <Link href={`/dashboards/${board.dashboard_id}?edit=1`} aria-label={`Edit ${board.title}`}>
                      <EditOutlined />
                    </Link>
                  </Tooltip>
                  <Popconfirm title="Delete this dashboard?" description="Its charts are kept." okText="Delete" okButtonProps={{ danger: true }} onConfirm={() => remove(board)}>
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} aria-label={`Delete ${board.title}`} />
                  </Popconfirm>
                </span>
              ),
          },
        ]}
      />
      <Modal title="New dashboard" open={creating} onCancel={() => setCreating(false)} onOk={create} okText="Create" confirmLoading={busy} okButtonProps={{ disabled: !title.trim() }}>
        <Input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Dashboard title" maxLength={120} onPressEnter={() => title.trim() && create()} />
      </Modal>
    </section>
  );
}
