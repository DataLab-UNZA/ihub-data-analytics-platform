import Link from 'next/link';
import { formatNumber } from '@/lib/format';

/**
 * Proportional stacked bar with a legend.
 *
 * @param {Array<{label: string, value: number, tone: 'accent'|'teal'|'blue', href?: string}>} segments
 */
export default function StackBar({ segments }) {
  const summary = segments.map((segment) => `${segment.label.toLowerCase()} ${formatNumber(segment.value)}`).join(', ');

  return (
    <>
      <div className="stack-bar" role="img" aria-label={`Publications by number of sources: ${summary}`}>
        {segments.map((segment) => (
          <span
            className={`stack-bar__seg stack-bar__seg--${segment.tone}`}
            key={segment.label}
            style={{ flex: segment.value }}
          />
        ))}
      </div>
      <ul className="legend">
        {segments.map((segment) => (
          <li className="legend__item" key={segment.label}>
            <span className={`legend__swatch legend__swatch--${segment.tone}`} aria-hidden="true" />
            <span>{segment.label}</span>
            <Link className="legend__value" href={segment.href ?? '#'}>
              {formatNumber(segment.value)}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
