import Link from 'next/link';

/**
 * Pagination footer: summary text on the left, page links on the right.
 *
 * Each entry of `pages` is a label string, "…" (a gap) or { label, href?, current? };
 * `previous` and `next` are labels or { label, href }. `href` is the default link target.
 */
export default function Pager({ summary, label, pages = [], previous, next, href = '#' }) {
  const target = (item) => (typeof item === 'object' && item.href ? item.href : href);
  const text = (item) => (typeof item === 'object' ? item.label : item);

  return (
    <nav className="pager" aria-label={label}>
      <p>{summary}</p>
      <div className="pager__links">
        {previous && (
          <Link href={target(previous)} rel="prev">
            {text(previous)}
          </Link>
        )}
        {pages.map((page, index) =>
          page === '…' ? (
            <span aria-hidden="true" key={`gap-${index}`}>
              …
            </span>
          ) : (
            <Link href={target(page)} key={text(page)} aria-current={page.current ? 'page' : undefined}>
              {text(page)}
            </Link>
          ),
        )}
        {next && (
          <Link href={target(next)} rel="next">
            {text(next)}
          </Link>
        )}
      </div>
    </nav>
  );
}
