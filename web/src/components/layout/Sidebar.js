import Link from 'next/link';
import { NAV_ITEMS } from '@/config/navigation';
import { roleLabel } from '@/config/roles';

/** Primary navigation, workspace label and refresh status. */
export default function Sidebar({ active, role, refreshed, ...props }) {
  return (
    <aside className="sidebar" id="sidebar" aria-label="Workspace" {...props}>
      <div className="brand">
        <span className="brand__name">iHub</span>
        <span className="brand__tag">Analytics</span>
      </div>

      <nav className="nav" aria-label="Primary">
        <ul className="nav__list">
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <Link className="nav__link" href={item.href} aria-current={item.id === active ? 'page' : undefined}>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar__footer">
        <div className="workspace">
          <p className="workspace__name">UNZA &bull; Research pilot</p>
          <p className="workspace__role">{roleLabel(role)} workspace</p>
        </div>
        <div className="refresh">
          <p className="refresh__label">Weekly refresh</p>
          <p className="refresh__date">{refreshed}</p>
        </div>
        <a className="sidebar__help" href="#definitions">
          Help &amp; data definitions
        </a>
      </div>
    </aside>
  );
}
