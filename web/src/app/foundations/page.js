import Sidebar from '@/components/layout/Sidebar';
import Topbar from '@/components/layout/Topbar';
import Button from '@/components/ui/Button';
import Alert from '@/components/ui/Alert';
import Card from '@/components/ui/Card';
import { Field, Input } from '@/components/ui/Form';
import { Kpi } from '@/components/ui/Kpi';
import { FiltersProvider } from '@/context/filters-context';
import { DEFAULT_REFRESHED } from '@/config/screens';

export const metadata = {
  title: 'Foundations',
  description: 'iHub Analytics design foundations: colour, typography, components, accessibility and data rules.',
};

const SWATCHES = [
  { name: 'canvas', hex: '#E1E7EF', outline: true },
  { name: 'surface', hex: '#FFFFFF', outline: true },
  { name: 'ink', hex: '#263746' },
  { name: 'muted', hex: '#5F6E7B' },
  { name: 'accent', hex: '#27BEDB' },
  { name: 'teal', hex: '#55C8B0' },
  { name: 'blue', hex: '#5C83E9' },
  { name: 'primary', hex: '#393F4B' },
];

/** Design-system reference. It embeds the real sidebar and top bar so the specimens stay in sync. */
export default function FoundationsPage() {
  return (
    <FiltersProvider>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <main className="doc" id="main">
        <header>
          <h1 className="doc__title">iHub Analytics / Foundations</h1>
          <p className="doc__lead">
            Extracted from the supplied login and analytics references • desktop 1440 / mobile 390
          </p>
        </header>

        <section className="doc__section" aria-labelledby="colour-title">
          <h2 className="doc__eyebrow" id="colour-title">
            Colour &amp; type
          </h2>
          <ul className="swatches">
            {SWATCHES.map((swatch) => (
              <li key={swatch.name}>
                <span
                  className={swatch.outline ? 'swatch__chip swatch__chip--outline' : 'swatch__chip'}
                  style={{ '--c': swatch.hex.toLowerCase() }}
                />
                <p className="swatch__name">{swatch.name}</p>
                <p className="swatch__hex">{swatch.hex}</p>
              </li>
            ))}
          </ul>

          <div className="type-specimen">
            <div>
              <p className="type-specimen__display">Executive overview</p>
              <p className="doc__lead">Roboto Condensed · dashboard headings and metrics</p>
            </div>
            <div>
              <p className="type-specimen__body">One trusted view of your organisation.</p>
              <p className="doc__lead">Poppins · forms, tables, navigation and supporting copy</p>
            </div>
          </div>
        </section>

        <section className="doc__section" aria-labelledby="components-title">
          <h2 className="sr-only" id="components-title">
            Components
          </h2>
          <div className="sample-row">
            <div className="btn-row btn-row--tight">
              <Button>Sign in</Button>
              <Button variant="secondary">Export report</Button>
            </div>
          </div>
          <div className="sample-row">
            <Field id="sample-email" label="Work email">
              <Input id="sample-email" type="email" placeholder="name@organisation.org" />
            </Field>
            <Kpi label="Total outputs" value="28,854" note="+8.2% vs last period" />
            <Card as="article">
              <h3 className="card__title">Card heading</h3>
              <p className="card__sub text-md mt-12">Source-linked, readable data.</p>
            </Card>
            <p className="panel">Overview</p>
          </div>
          <div className="sample-row sample-row--status">
            <label className="filter" htmlFor="sample-period" style={{ flex: 'none' }}>
              <span>Period:</span>
              <select id="sample-period" defaultValue="All years">
                <option>All years</option>
                <option>2026</option>
              </select>
            </label>
            <p>
              <span className="badge">Up to date</span>
            </p>
            <Alert id="refresh-title" tone="text-link" title="Weekly refresh complete · 16 November 2026">
              Missing values display as Unknown, never as zero.
            </Alert>
          </div>
        </section>

        <section className="doc__section" aria-labelledby="rules-title">
          <h2 className="doc__eyebrow" id="rules-title">
            Accessibility &amp; data rules
          </h2>
          <p className="rule-block">
            44 px minimum targets · visible keyboard focus · labels on every field · dark text on cyan accents
          </p>
          <p className="rule-block">
            Organisation &gt; Unit &gt; Member · renameable hierarchy · A–Z members, never ranked · role-limited individual
            views
          </p>
          <p className="rule-block">
            Pilot facts: 28,854 publications · 13 schools · 77 departments · OpenAlex, ORCID, repository and 15 journals.
          </p>
          <p className="rule-block rule-block--foot">
            Other figures in this design preview are illustrative. Charts and export screens do not imply live connections.
          </p>
        </section>

        <div className="demo-shell">
          <Sidebar active="overview" role="executive" refreshed={DEFAULT_REFRESHED} aria-label="Sidebar example" />
          <div>
            <Topbar role="executive" aria-label="Top bar example" />

            <section aria-labelledby="states-title">
              <h2 className="doc__eyebrow" id="states-title">
                Control states
              </h2>
              <div className="states-row">
                <figure>
                  <Button size="sm">Sign in</Button>
                  <figcaption>Default</figcaption>
                </figure>
                <figure>
                  <Button size="sm" className="btn--focus">
                    Sign in
                  </Button>
                  <figcaption>Focus · 3px ring</figcaption>
                </figure>
                <figure>
                  <Button size="sm" className="btn--ghost-disabled" disabled>
                    Sign in
                  </Button>
                  <figcaption>Disabled</figcaption>
                </figure>
              </div>

              <div className="demo-field">
                <Field id="sample-invalid" label="Work email" error="Enter a valid work email address.">
                  <Input
                    id="sample-invalid"
                    type="email"
                    defaultValue="name@"
                    aria-invalid="true"
                    aria-describedby="sample-invalid-error"
                  />
                </Field>
              </div>

              <div className="mt-48">
                <Alert id="refresh-failed" role="status" title="Source refresh failed">
                  Keep the last successful snapshot, show its date, and offer a recovery action.
                </Alert>
              </div>

              <h2 className="doc__eyebrow mt-48" id="contract-title">
                Behaviour contract
              </h2>
              <p className="rule-block">
                Global filters persist across every signed-in page. Numbers and chart marks open the filtered source
                record list.
              </p>
              <p className="rule-block mt-32">
                Authorised individuals are listed A–Z only. Unit heads are scoped to their own unit and sub-units.
                Exports honour the same access rules.
              </p>
              <p className="rule-block mt-32">
                Chart colours mirror the reference; dark labels and outlines carry meaning without relying on colour
                alone. Accessible tables accompany visual charts in implementation.
              </p>
              <p className="rule-block rule-block--foot">
                These are editable interface designs, not connected dashboards. Credentials, integrations, exports and
                permissions are represented as interface states.
              </p>
            </section>
          </div>
        </div>
      </main>
    </FiltersProvider>
  );
}
