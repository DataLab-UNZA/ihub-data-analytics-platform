import { cx } from '@/lib/format';

/**
 * Radio group rendered as selectable cards.
 *
 * @param {string} legend Accessible group name (visually hidden unless `visibleLegend`).
 * @param {Array<{value: string, title: string, description?: string, chevron?: boolean}>} items
 * @param {string} defaultValue Initially selected value.
 * @param {boolean} row Lay the cards out in three columns.
 */
export default function ChoiceGroup({ legend, name, items, defaultValue, row = false, visibleLegend = false }) {
  return (
    <fieldset>
      <legend className={visibleLegend ? 'legend-label' : 'sr-only'}>{legend}</legend>
      <div className={cx('choice-group', row && 'choice-group--row')}>
        {items.map((item) => (
          <label className="choice" key={item.value}>
            <input className="choice__input" type="radio" name={name} value={item.value} defaultChecked={item.value === defaultValue} />
            <span className="choice__body">
              {item.chevron && (
                <span className="choice__chevron" aria-hidden="true">
                  ›
                </span>
              )}
              <span className="choice__title">{item.title}</span>
              {item.description && <span className="choice__desc">{item.description}</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
