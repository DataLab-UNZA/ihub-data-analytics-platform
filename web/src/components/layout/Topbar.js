'use client';

import { ROLES } from '@/config/roles';
import { useFilters } from '@/context/filters-context';

/** Workspace switcher, global search, period filter and role switcher. */
export default function Topbar({ role, menuOpen = false, onToggleMenu, ...props }) {
  const { values, definitions, setFilter } = useFilters();
  const period = definitions.find((filter) => filter.key === 'period');

  return (
    <header className="topbar" {...props}>
      {onToggleMenu && (
        <button
          className="menu-toggle"
          type="button"
          aria-controls="sidebar"
          aria-expanded={menuOpen}
          onClick={onToggleMenu}
        >
          Menu
        </button>
      )}

      <div className="topbar__org">
        <label className="sr-only" htmlFor="workspace-switcher">
          Workspace
        </label>
        <select className="select-plain" id="workspace-switcher" name="workspace" defaultValue="University of Zambia">
          <option>University of Zambia</option>
          <option>Ministry workspace</option>
        </select>
      </div>

      <form className="topbar__search" role="search" action="/search" method="get">
        <label className="sr-only" htmlFor="global-search">
          Search records, units and members
        </label>
        <input
          id="global-search"
          type="search"
          name="q"
          placeholder="Search records, units, members…"
          autoComplete="off"
        />
      </form>

      <div className="topbar__period">
        <label className="sr-only" htmlFor="topbar-period">
          Period
        </label>
        <select
          className="select-plain"
          id="topbar-period"
          name="period"
          value={values.period}
          onChange={(event) => setFilter('period', event.target.value)}
        >
          {period.options.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="topbar__role">
        <label className="sr-only" htmlFor="role-switcher">
          Role
        </label>
        <select className="select-plain" id="role-switcher" name="role" key={role} defaultValue={role}>
          {ROLES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
