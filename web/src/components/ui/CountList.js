import { formatNumber } from '@/lib/format';

/**
 * Compact label and count pairs, e.g. publications by source.
 *
 * @param {Array<{label: string, value: number|null}>} items A null value is shown as "–" (no data).
 * @param {string} label Accessible name of the list.
 */
export default function CountList({ items, label, className }) {
  return (
    <dl className={['count-list', className].filter(Boolean).join(' ')} aria-label={label}>
      {items.map((item) => (
        <div className="count-list__row" key={item.label}>
          <dt>{item.label}</dt>
          <dd title={item.value === null ? 'No data for this source' : undefined}>
            {item.value === null ? '–' : formatNumber(item.value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
