'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Empty, Input } from 'antd';
import { SearchOutlined, ToolOutlined } from '@ant-design/icons';
import { VIZ_ICONS } from './icons';

/**
 * The start of Explore: ready-made charts grouped by theme, each a plain-language question.
 * A search box narrows them; "build your own" opens the advanced chart builder.
 *
 * @param {Array} themes Themes with their guides (from /api/explore/guides), already limited to
 *   what this visitor may see.
 * @param {boolean} canBuild Whether to offer the chart builder.
 */
export default function ExploreHome({ themes, canBuild }) {
  const [search, setSearch] = useState('');
  const term = search.trim().toLowerCase();
  const shown = themes
    .map((theme) => ({
      ...theme,
      guides: theme.guides.filter((guide) => !term || `${guide.title} ${guide.question} ${theme.title}`.toLowerCase().includes(term)),
    }))
    .filter((theme) => theme.guides.length);

  return (
    <div className="guide-home">
      <div className="guide-home__tools">
        <Input
          size="large"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Search the questions, for example “open access” or “citations”"
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

      {shown.length === 0 && <Empty description="No chart matches that search." />}

      {shown.map((theme) => (
        <section className="guide-theme" key={theme.key} aria-labelledby={`theme-${theme.key}`}>
          <h2 className="guide-theme__title" id={`theme-${theme.key}`}>
            {theme.title}
          </h2>
          <p className="guide-theme__blurb">{theme.blurb}</p>
          <ul className="guide-grid">
            {theme.guides.map((guide) => (
              <li key={guide.id}>
                <Link className="guide-card" href={`/explore/guide/${guide.id}`}>
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
    </div>
  );
}
