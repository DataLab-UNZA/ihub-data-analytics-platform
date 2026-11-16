'use client';

import { FILTER_DEFAULTS, optionLabel } from '@/config/filters';
import { useFilters } from '@/context/filters-context';
import Chip from '@/components/ui/Chip';

const NAMES = { period: 'period', unit: 'unit', source: 'source', type: 'type' };

/** Removable chips for every global filter that differs from its default. */
export default function ActiveFilterChips() {
  const { values, definitions, resetFilters } = useFilters();
  const active = Object.keys(NAMES).filter((key) => values[key] !== FILTER_DEFAULTS[key]);

  if (active.length === 0) {
    return null;
  }

  return (
    <ul className="chip-list chip-list--panel" aria-label="Active filters">
      {active.map((key) => (
        <li key={key}>
          <Chip srLabel={`Remove ${NAMES[key]} filter`} onClick={() => resetFilters(key)}>
            {optionLabel(definitions, key, values[key])}
          </Chip>
        </li>
      ))}
    </ul>
  );
}
