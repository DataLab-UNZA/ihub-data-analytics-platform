'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { App, Checkbox, Input, Modal, Select } from 'antd';
import { bff } from './client';

function Label({ children }) {
  return (
    <div className="control-label">
      <span>{children}</span>
    </div>
  );
}

/**
 * Saves a chart (new, or over the one being edited) and can add it to a dashboard.
 * Used by the chart builder and by the ready-made charts.
 *
 * @param {object|null} chart  The saved chart being edited, if any.
 * @param {boolean} canEdit    Whether the user may change `chart`.
 * @param {string} name        Suggested name.
 * @param {() => object} getBody  Returns { viz_type, params, options } for the chart as shown now.
 * @param {Array} dashboards   Dashboards the user could add the chart to.
 * @param {(chart: object) => void} onSaved  Called with the saved chart.
 */
export default function SaveChartModal({ open, onClose, chart = null, canEdit = true, name, description = '', getBody, dashboards = [], onSaved }) {
  const router = useRouter();
  const { message } = App.useApp();
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', description, dashboard: null, asNew: false });

  const save = async () => {
    setSaving(true);
    try {
      const body = { name: form.name || name, description: form.description, ...getBody() };
      const saved =
        chart && canEdit && !form.asNew
          ? await bff(`charts/${chart.chart_id}`, { method: 'PATCH', body })
          : await bff('charts', { method: 'POST', body });
      if (form.dashboard) {
        const board = await bff(`dashboards/${form.dashboard}`);
        if (!board.items.some((item) => item.chart_id === saved.chart_id)) {
          await bff(`dashboards/${form.dashboard}`, {
            method: 'PATCH',
            body: { items: [...board.items, { chart_id: saved.chart_id, width: 6, height: 8 }] },
          });
        }
      }
      message.success(form.dashboard ? 'Chart saved and added to the dashboard.' : 'Chart saved.');
      onClose();
      onSaved?.(saved);
      router.refresh();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={chart ? 'Save chart' : 'Save new chart'} open={open} onCancel={onClose} onOk={save} okText="Save" confirmLoading={saving}>
      <div className="stack stack--sm">
        {chart && canEdit && (
          <Checkbox checked={form.asNew} onChange={(e) => setForm({ ...form, asNew: e.target.checked })}>
            Save as a new chart
          </Checkbox>
        )}
        <Label>CHART NAME</Label>
        <Input value={form.name || name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={120} />
        <Label>DESCRIPTION</Label>
        <Input.TextArea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} maxLength={500} rows={2} />
        <Label>ADD TO DASHBOARD</Label>
        <Select
          className="w-full"
          allowClear
          placeholder="Optional"
          value={form.dashboard}
          onChange={(dashboard) => setForm({ ...form, dashboard })}
          options={dashboards.filter((d) => d.can_edit).map((d) => ({ value: d.dashboard_id, label: d.title }))}
        />
      </div>
    </Modal>
  );
}
