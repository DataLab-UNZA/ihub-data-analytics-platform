'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Empty, Input, Tag } from 'antd';
import { SearchOutlined, ToolOutlined } from '@ant-design/icons';
import { VIZ_ICONS } from './icons';

const matches = (term, ...texts) => !term || texts.join(' ').toLowerCase().includes(term);

/**
 * The start of Explore: ready-made charts grouped by module (research, then the modules that
 * are not connected yet, with sample data), and within a module by theme. Each chart is a
 * plain-language question. A search box narrows them; "build your own" opens the chart builder.
 *
 * @param {Array} modules Modules with their themes and guides (from loadModules), already
 *   limited to what this visitor may see. Each guide carries the `href` it opens at.
 * @param {boolean} canBuild Whether to offer the chart builder.
 */
export default function ExploreHome({ modules, canBuild }) {
  const [search, setSearch] = useState('');
  const term = search.trim().toLowerCase();
  const shown = modules
    .map((chartModule) => ({
      ...chartModule,
      themes: chartModule.themes
        .map((theme) => ({
          ...theme,
          guides: theme.guides.filter((guide) => matches(term, guide.title, guide.question, theme.title, chartModule.title)),
        }))
        .filter((theme) => theme.guides.length),
    }))
    .filter((chartModule) => chartModule.themes.length);

  return (
    <div className="guide-home">
      <div className="guide-home__tools">
        <Input
          size="large"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Search the questions, for example “open access” or “enrolment”"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search ready-made charts"
        />
        {canBuild && (
          <Link className="guide-home__build" href="/explore/build">
            <ToolOutlined /> Build your own chart
            <small>Choose the data, measures and chart type yourself</small>
          </Link>
        )}
      </div>

      {shown.length > 1 && (
        <nav className="module-nav" aria-label="Modules">
          {shown.map((chartModule) => (
            <a key={chartModule.key} href={`#module-${chartModule.key}`}>
              {chartModule.title}
            </a>
          ))}
        </nav>
      )}

      {shown.length === 0 && <Empty description="No chart matches that search." />}

      {shown.map((chartModule) => (
        <section className="guide-module" key={chartModule.key} id={`module-${chartModule.key}`} aria-labelledby={`module-title-${chartModule.key}`}>
          <header className="guide-module__head">
            <h2 className="guide-module__title" id={`module-title-${chartModule.key}`}>
              {chartModule.title}
              {chartModule.status === 'sample' && <Tag className="featured__tag">Sample data</Tag>}
            </h2>
            {chartModule.status === 'live' && <p className="guide-module__blurb">{chartModule.blurb}</p>}
          </header>

          {chartModule.themes.map((theme) => (
            <section className="guide-theme" key={theme.key} aria-labelledby={`theme-${theme.key}`}>
              <h3 className="guide-theme__title" id={`theme-${theme.key}`}>
                {theme.title}
              </h3>
              <p className="guide-theme__blurb">{theme.blurb}</p>
              <ul className="guide-grid">
                {theme.guides.map((guide) => (
                  <li key={guide.id}>
                    <Link className="guide-card" href={guide.href}>
                      <span className="guide-card__icon" aria-hidden="true">
                        {VIZ_ICONS[guide.viz]}
                      </span>
                      <span className="guide-card__text">
                        <strong>{guide.title}</strong>
                        <small>{guide.question}</small>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </section>
      ))}
    </div>
  );
}
