import Link from 'next/link';
import GlobalFilters from './GlobalFilters';

/**
 * Page title, breadcrumb and the global filter bar.
 * Every signed-in screen starts with one of these.
 *
 * @param {string} title   The page's single <h1>.
 * @param {node}   aside   Optional short status text shown beside the title.
 * @param {boolean} filters Set to false to omit the filter bar.
 */
export default function PageHeader({ title, aside, filters = true }) {
  return (
    <>
      <header className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <ol>
              <li>
                <Link href="/overview">University of Zambia</Link>
              </li>
              <li aria-current="page">Research intelligence</li>
            </ol>
          </nav>
        </div>
        {aside && <p className="page-header__aside">{aside}</p>}
      </header>
      {filters && <GlobalFilters />}
    </>
  );
}
