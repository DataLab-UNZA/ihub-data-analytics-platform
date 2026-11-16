import Link from 'next/link';
import { cx, formatNumber } from '@/lib/format';

/**
 * Horizontal bar list built on <meter>, so the values are exposed to assistive technology.
 *
 * @param {Array<{label: string, value: number, tone?: 'teal'|'blue', href?: string}>} items
 * @param {number} max Scale maximum shared by all bars.
 * @param {string} unit Noun used in each bar's accessible name.
 */
export default function BarList({ items, max, unit = 'outputs', spacious = false }) {
  return (
    <ul className={cx('bar-list', spacious && 'bar-list--spacious')}>
      {items.map((item) => (
        <li className="bar-list__item" key={item.label}>
          {item.href ? (
            <Link className="bar-list__label" href={item.href}>
              {item.label}
            </Link>
          ) : (
            <span className="bar-list__label">{item.label}</span>
          )}
          <span className="bar-list__value">{formatNumber(item.value)}</span>
          <meter
            className={cx('bar', item.tone && `bar--${item.tone}`)}
            min={0}
            max={max}
            value={item.value}
            aria-label={`${item.label}: ${formatNumber(item.value)} ${unit}`}
          />
        </li>
      ))}
    </ul>
  );
}
