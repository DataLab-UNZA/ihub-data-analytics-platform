'use client';

import { useMemo } from 'react';
import EChart from '@/components/charts/EChart';
import { categorical } from '@/theme/tokens';
import { cx, formatNumber } from '@/lib/format';

const SHORT_NAME = /^(School of|Institute of|Directorate of|Graduate School of)\s+/;

/** "School of Medicine" -> "Medicine": the legend is narrow and every unit has to fit. */
const shortName = (name) => name.replace(SHORT_NAME, '');

const colourOf = (index) => categorical[index % categorical.length];

/**
 * Compact pie of how the period's publications are spread across the units, with a legend that
 * names every unit and its count. The selected unit is pulled out of the pie.
 *
 * @param {Array<{id: string, name: string, count: number}>} slices Units with publications.
 * @param {number} emptyUnits How many units have none in the period (named in the caption).
 * @param {string} selectedId Id of the selected tree node.
 * @param {(id: string) => void} onSelect Called when a slice or legend entry is chosen.
 */
export default function UnitPie({ slices, emptyUnits = 0, selectedId, onSelect }) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);

  const option = useMemo(
    () => ({
      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: ({ name, value, percent }) => `${name}<br/>${formatNumber(value)} publications (${percent}%)`,
      },
      series: [
        {
          type: 'pie',
          radius: '92%',
          center: ['50%', '50%'],
          label: { show: false },
          labelLine: { show: false },
          selectedMode: 'single',
          selectedOffset: 6,
          itemStyle: { borderColor: '#ffffff', borderWidth: 1 },
          emphasis: { scaleSize: 3 },
          data: slices.map((slice, index) => ({
            id: slice.id,
            name: slice.name,
            value: slice.count,
            selected: slice.id === selectedId,
            itemStyle: { color: colourOf(index) },
          })),
        },
      ],
    }),
    [slices, selectedId],
  );

  if (!total) {
    return <p className="text-muted">No unit has publications in this period.</p>;
  }

  return (
    <>
      <EChart
        option={option}
        height={168}
        ariaLabel={`Pie chart of ${formatNumber(total)} publication credits across ${slices.length} units`}
        onClick={(event) => event.data?.id && onSelect(event.data.id)}
      />
      <ul className="pie-legend" aria-label="Publications per unit">
        {slices.map((slice, index) => (
          <li key={slice.id}>
            <button
              type="button"
              className={cx('pie-legend__item', slice.id === selectedId && 'is-selected')}
              aria-pressed={slice.id === selectedId}
              title={`${slice.name}: ${formatNumber(slice.count)} publications`}
              onClick={() => onSelect(slice.id)}
            >
              <span className="pie-legend__swatch" style={{ background: colourOf(index) }} aria-hidden="true" />
              <span className="pie-legend__name">{shortName(slice.name)}</span>
              <span className="pie-legend__value">{formatNumber(slice.count)}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="text-muted text-xs mt-12">
        A publication with authors in several units counts in each.
        {emptyUnits > 0 && ` ${emptyUnits} unit${emptyUnits === 1 ? ' has' : 's have'} no publications in this period.`}
      </p>
    </>
  );
}
