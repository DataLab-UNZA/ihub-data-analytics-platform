'use client';

import { useState } from 'react';
import Link from 'next/link';
import Card, { CardHeader } from '@/components/ui/Card';
import { cx } from '@/lib/format';

function matches(item, filter) {
  if (filter === 'all') return true;
  if (filter === 'unread') return Boolean(item.unread);
  return item.category === filter;
}

/**
 * Notification list with filter tabs.
 *
 * @param {Array} items Notifications (see src/data/workspace.js).
 * @param {Array<{id: string, label: string}>} tabs Filter tabs.
 */
export default function NotificationCenter({ items, tabs }) {
  const [filter, setFilter] = useState('all');
  const visible = items.filter((item) => matches(item, filter));

  return (
    <Card aria-labelledby="notices-title">
      <CardHeader id="notices-title" title="Your notifications" className="card__head--flush">
        <div className="filter-tabs" role="group" aria-label="Filter notifications">
          {tabs.map((tab) => (
            <button
              className="filter-tabs__btn"
              type="button"
              key={tab.id}
              aria-pressed={filter === tab.id}
              onClick={() => setFilter(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <p className="sr-only" role="status" aria-live="polite">
          {visible.length} {visible.length === 1 ? 'notification' : 'notifications'} shown
        </p>
      </CardHeader>

      <ul className="notice-list">
        {visible.map((item) => (
          <li key={item.id}>
            <article>
              <h3 className="notice__title">{item.title}</h3>
              <p className="notice__text">{item.text}</p>
            </article>
            <div className="notice__side">
              <time className={cx('notice__time')} dateTime={item.iso}>
                {item.time}
              </time>
              <Link href={item.href}>{item.action}</Link>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
