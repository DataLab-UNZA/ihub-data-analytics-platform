'use client';

import { useState } from 'react';
import Card, { CardHeader } from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';
import { brandingDefaults, brandingPreviewBars } from '@/data/admin';

/** Workspace appearance form beside a live preview that follows the accent colour. */
export default function BrandingEditor() {
  const [accent, setAccent] = useState(brandingDefaults.accent);

  return (
    <Grid variant="halves">
      <Card aria-labelledby="appearance-title">
        <CardHeader
          id="appearance-title"
          title="Workspace appearance"
          subtitle="Branding is applied to your workspace and future exports"
        />
        <form className="form-grid" action="/admin/branding" method="post" encType="multipart/form-data">
          <Field id="display-name" label="Display name">
            <Input id="display-name" name="display-name" type="text" defaultValue={brandingDefaults.displayName} required />
          </Field>
          <Field id="product-name" label="Product name">
            <Input id="product-name" name="product-name" type="text" defaultValue={brandingDefaults.productName} required />
          </Field>
          <div>
            <p className="legend-label" id="wordmark-label">
              Wordmark
            </p>
            <p className="wordmark-box" aria-labelledby="wordmark-label">
              {brandingDefaults.productName}
            </p>
          </div>
          <div className="upload-field">
            <label className="btn btn--secondary btn--md" htmlFor="wordmark-file">
              Replace wordmark
            </label>
            <input className="sr-only" id="wordmark-file" name="wordmark" type="file" accept="image/svg+xml,image/png" />
          </div>
          <Field id="accent-colour" label="Accent colour">
            <div className="color-field">
              <input
                id="accent-colour"
                name="accent"
                type="color"
                value={accent}
                onChange={(event) => setAccent(event.target.value)}
              />
              <output htmlFor="accent-colour">{accent.toUpperCase()}</output>
            </div>
          </Field>
          <div>
            <Button size="md" type="submit">
              Save branding
            </Button>
          </div>
        </form>
      </Card>

      <Card aria-labelledby="preview-title">
        <CardHeader id="preview-title" title="Preview" subtitle="Readable defaults are preserved across all themes" />
        <div className="brand-preview" aria-hidden="true" style={{ '--accent': accent }}>
          <div className="brand-preview__side">
            <span className="brand__name">iHub</span>
            <p className="brand-preview__nav">Overview</p>
          </div>
          <div className="brand-preview__main">
            <div className="brand-preview__card">
              <p className="meta-label">Total outputs</p>
              <p className="big-figure mt-16">28,854</p>
            </div>
            <div className="brand-preview__card">
              <div className="brand-preview__bars">
                {brandingPreviewBars.map((height) => (
                  <span key={height} style={{ '--h': height }} />
                ))}
              </div>
            </div>
          </div>
        </div>
        <h3 className="mt-48">Contrast protection</h3>
        <p className="text-muted mt-16">
          Accent colours are used for charts and selected surfaces. Dark text and visible focus outlines keep key
          controls legible.
        </p>
        <p className="mt-48 text-sm">
          <a href="#publishing">All changes can be reviewed before publishing.</a>
        </p>
      </Card>
    </Grid>
  );
}
