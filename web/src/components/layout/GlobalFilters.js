'use client';

import { useFilters } from '@/context/filters-context';

/** The four global filters (period, unit, source, type) with a reset action. */
export default function GlobalFilters() {
  const { values, definitions, setFilter, resetFilters } = useFilters();

  return (
    <form className="filters" aria-label="Global filters" onSubmit={(event) => event.preventDefault()}>
      {definitions.map((filter) => {
        const id = `filter-${filter.key}`;
        return (
          <label className="filter" htmlFor={id} key={filter.key}>
            <span>{filter.label}:</span>
            <select
              id={id}
              name={filter.key}
              value={values[filter.key]}
              onChange={(event) => setFilter(filter.key, event.target.value)}
            >
              {filter.options.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        );
      })}
      <button className="filters__reset" type="button" onClick={() => resetFilters()}>
        Reset
      </button>
    </form>
  );
}
