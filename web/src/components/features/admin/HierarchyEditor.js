'use client';

import { useState } from 'react';
import Card, { CardHeader } from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';
import { hierarchyFields } from '@/data/admin';

/** Level-label form beside a live preview of the renamed hierarchy. */
export default function HierarchyEditor() {
  const [labels, setLabels] = useState(() =>
    Object.fromEntries(hierarchyFields.map((field) => [field.key, field.defaultValue])),
  );

  const labelFor = (field) => labels[field.key].trim() || field.defaultValue;
  const preview = Object.fromEntries(hierarchyFields.map((field) => [field.key, labelFor(field)]));

  return (
    <Grid variant="halves">
      <Card aria-labelledby="name-title">
        <CardHeader id="name-title" title="Name your hierarchy" subtitle="Generic model: Organisation > Unit > Member" />
        <form className="form-grid" action="/admin/hierarchy" method="post">
          {hierarchyFields.map((field) => (
            <Field id={field.id} label={field.label} key={field.key}>
              <Input
                id={field.id}
                name={field.key}
                type="text"
                value={labels[field.key]}
                onChange={(event) => setLabels((current) => ({ ...current, [field.key]: event.target.value }))}
                required
              />
            </Field>
          ))}
          <div>
            <Button size="md" type="submit">
              Save labels
            </Button>
          </div>
        </form>
      </Card>

      <Card aria-labelledby="preview-title" aria-live="polite">
        <CardHeader
          id="preview-title"
          title="Live label preview"
          subtitle="Labels change the interface, not source records"
        />
        <p className="preview-tree__root mt-32">University of Zambia</p>
        <ul className="preview-tree">
          <li className="preview-tree__item preview-tree__item--l1">{preview.level1} of Medicine</li>
          <li className="preview-tree__item preview-tree__item--l2">{preview.level2} of Public Health</li>
          <li className="preview-tree__item preview-tree__item--l3">{preview.individual}</li>
        </ul>
        <hr className="divider mt-40" />
        <h3 className="subhead--plain text-md">For a ministry</h3>
        <p className="text-muted mt-16">Organisation &gt; Directorate &gt; Unit &gt; Member</p>
        <p className="text-muted mt-48">Rename levels without breaking comparisons or historic reports.</p>
      </Card>
    </Grid>
  );
}
