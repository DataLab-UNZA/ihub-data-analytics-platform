'use client';

import Link from 'next/link';
import { ArrowRightOutlined, ExperimentOutlined, IdcardOutlined, TeamOutlined } from '@ant-design/icons';
import ChartView from '@/components/charts/ChartView';
import LineChart from '@/components/charts/LineChart';
import { LiveChart } from '@/components/features/charts/FeaturedCharts';
import BarList from '@/components/ui/BarList';
import Card, { CardHeader } from '@/components/ui/Card';
import Grid from '@/components/ui/Grid';
import { cx, formatNumber, pointsChange } from '@/lib/format';
import { DEFAULT_OPTIONS } from '@/lib/viz';

const MODULE_ICONS = {
  research: <ExperimentOutlined />,
  students: <TeamOutlined />,
  hr: <IdcardOutlined />,
};

/** "Live" for connected data, "Sample data" for modules that are not connected yet. */
function StatusBadge({ status }) {
  return (
    <span className={cx('status-badge', `status-badge--${status}`)}>{status === 'live' ? 'Live' : 'Sample data'}</span>
  );
}

/** One area of the university (research, student information, HR): its headline and a way in. */
function ModuleCard({ item }) {
  return (
    <Link className="card module-card" href={item.href} aria-labelledby={`module-card-${item.key}`}>
      <span className="module-card__top">
        <span className="module-card__icon" aria-hidden="true">
          {MODULE_ICONS[item.key]}
        </span>
        <StatusBadge status={item.status} />
      </span>
      <span className="module-card__title" id={`module-card-${item.key}`}>
        {item.title}
      </span>
      <span className="module-card__source">{item.source}</span>
      <span className="module-card__value">{item.value}</span>
      <span className="module-card__label">{item.valueLabel}</span>
      <span className="module-card__stats">
        {item.stats.map((stat) => (
          <span className="module-card__stat" key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </span>
        ))}
      </span>
      <span className="module-card__cta">
        {item.cta} <ArrowRightOutlined />
      </span>
    </Link>
  );
}

/** A section heading inside the dashboard, with an optional badge and link. */
function SectionHead({ id, title, sub, status, link }) {
  return (
    <header className="dash-section__head">
      <div>
        <h2 className="dash-section__title" id={id}>
          {title}
          {status && <StatusBadge status={status} />}
        </h2>
        <p className="dash-section__sub">{sub}</p>
      </div>
      {link && (
        <Link className="dash-section__link" href={link.href}>
          {link.label} <ArrowRightOutlined />
        </Link>
      )}
    </header>
  );
}

/** Research highlights: what changed and where to act, from the live research data. */
function ResearchHighlights({ research }) {
  const oaUp = research.oaChange === null || research.oaChange >= 0;
  return (
    <Card aria-labelledby="highlights-title">
      <CardHeader id="highlights-title" title="Research highlights" subtitle="From the latest refresh of the research sources" />
      <ul className="highlights">
        <li>
          <p className="eyebrow">Open access</p>
          <h3>{oaUp ? 'More research is freely available' : 'Open-access share fell'}</h3>
          <p className="card__sub">
            {research.oaChange === null
              ? `${(research.oaShare * 100).toFixed(1)}% of outputs in this period are open access.`
              : `${pointsChange(research.oaShare, research.oaShare - research.oaChange)} compared with the previous period.`}
          </p>
        </li>
        {research.topPartner && (
          <li>
            <p className="eyebrow">Collaboration</p>
            <h3>{research.topPartner.name} is the top partner country</h3>
            <p className="card__sub">
              <Link href="/collaboration">{formatNumber(research.topPartner.publications)} co-authored outputs →</Link>
            </p>
          </li>
        )}
        <li>
          <p className="eyebrow">Repository</p>
          <h3>{formatNumber(research.missingFromRepository)} outputs are not in the repository</h3>
          <p className="card__sub">
            <Link href="/coverage">Review repository coverage →</Link>
          </p>
        </li>
      </ul>
    </Card>
  );
}

const PEOPLE_CHART_HEIGHT = 280;

/** One chart from a source system (IRIMS, Moodle or the HR system): live data or a sample. */
function PeopleChartCard({ chart }) {
  return (
    <Card className="dash-chart" aria-labelledby={`dash-${chart.id}`}>
      <header className="card__head">
        <p className="dash-chart__meta">
          <span className="dash-chart__source">
            {chart.source} · {chart.area}
          </span>
          <StatusBadge status={chart.status} />
        </p>
        <h3 className="card__title" id={`dash-${chart.id}`}>
          <Link href={chart.href}>{chart.title}</Link>
        </h3>
        <p className="card__sub">{chart.question}</p>
      </header>
      {chart.spec ? (
        <LiveChart guide={chart} height={PEOPLE_CHART_HEIGHT} />
      ) : (
        <ChartView viz={chart.viz} result={chart.result} options={{ ...DEFAULT_OPTIONS, ...chart.options }} height={PEOPLE_CHART_HEIGHT} />
      )}
    </Card>
  );
}

/**
 * The institutional dashboard: one card per area (research, student information, HR), the
 * three research charts that matter most, one chart each from IRIMS, Moodle and the HR system,
 * ratios across systems and the state of every source. Research and IRIMS are live; student
 * records, Moodle and HR show sample data, clearly labelled, until they are connected.
 *
 * @param {object} data From services/dashboard.js (loadDashboard).
 */
export default function InstitutionDashboard({ data }) {
  const { research } = data;
  const period = research.years.start === research.years.end ? `${research.years.start}` : `${research.years.start} to ${research.years.end}`;

  return (
    <div className="dash">
      <Grid as="section" variant="thirds" aria-label="Areas of the university">
        {data.modules.map((item) => (
          <ModuleCard key={item.key} item={item} />
        ))}
      </Grid>

      <section className="dash-section" aria-labelledby="dash-research">
        <SectionHead
          id="dash-research"
          title="Research"
          sub={`Live data · ${period} · follows the period and filters above`}
          status="live"
          link={{ href: '/explore#module-research', label: 'All research charts' }}
        />
        <Grid variant="main-aside">
          <Card aria-labelledby="dash-output">
            <CardHeader id="dash-output" title="Research output over time" subtitle="Outputs by year · select a point to see the records" />
            <LineChart
              id="dashboard-output"
              caption={`Research output per year, ${period}`}
              data={research.series}
              max={research.scale.max}
              step={research.scale.step}
              drillHref="/publications"
            />
          </Card>
          <Card aria-labelledby="dash-units">
            <CardHeader id="dash-units" title="Outputs by school" subtitle={`Top five of ${research.schoolCount} units · a publication counts once in each school`} />
            <BarList items={research.schools} max={research.schoolMax} />
          </Card>
        </Grid>
        <Grid variant="main-aside">
          <Card aria-labelledby="dash-oa">
            <CardHeader
              id="dash-oa"
              title="Open-access share over time"
              subtitle="Share of each year's outputs that anyone can read · years with fewer than 50 outputs are left out"
            />
            <ChartView viz="line" result={data.oa} options={{ ...DEFAULT_OPTIONS, show_legend: false }} height={300} />
          </Card>
          <ResearchHighlights research={research} />
        </Grid>
      </section>

      <section className="dash-section" aria-labelledby="dash-people">
        <SectionHead
          id="dash-people"
          title="Students and staff"
          sub="One chart from each system: IRIMS for students' dissertations and theses, Moodle for learning and the HR system for staff."
          link={{ href: '/charts', label: 'More charts' }}
        />
        <Grid variant="thirds">
          {data.people.map((chart) => (
            <PeopleChartCard key={chart.id} chart={chart} />
          ))}
        </Grid>
      </section>

      <Grid variant="halves" className="dash-section">
        <Card aria-labelledby="dash-ratios">
          <CardHeader id="dash-ratios" title="Across the university" subtitle="Ratios that join systems · each shows the data it rests on" />
          <dl className="ratios">
            {data.ratios.map((ratio) => (
              <div className="ratios__item" key={ratio.label}>
                <dt>{ratio.label}</dt>
                <dd>
                  <strong>{ratio.value}</strong>
                  <span>{ratio.basis}</span>
                </dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card aria-labelledby="dash-sources">
          <CardHeader
            id="dash-sources"
            title="Data sources"
            subtitle={`Research refreshes weekly · last run ${data.sources.lastRun ?? 'not recorded'}`}
          />
          <ul className="source-status">
            {data.sources.rows.map((row) => (
              <li key={row.name}>
                <span className={cx('source-status__dot', `source-status__dot--${row.status}`)} aria-hidden="true" />
                <span className="source-status__name">{row.name}</span>
                <span className="source-status__detail">{row.detail}</span>
                <StatusBadge status={row.status} />
              </li>
            ))}
          </ul>
          <p className="card__foot">
            <Link href="/data-sources">Manage data sources →</Link>
          </p>
        </Card>
      </Grid>
    </div>
  );
}
