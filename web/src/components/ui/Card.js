import { cx } from '@/lib/format';

/** White surface used for every block of content. Render as <section>, <article> etc. with `as`. */
export default function Card({ as: Tag = 'section', className, children, ...props }) {
  return (
    <Tag className={cx('card', className)} {...props}>
      {children}
    </Tag>
  );
}

/**
 * Card heading with an optional sub-line.
 *
 * @param {string} id        Id for the <h2>; pair it with `aria-labelledby` on the card.
 * @param {string} as        Heading element (defaults to h2).
 * @param {node}   subtitle  Muted line below the heading.
 */
export function CardHeader({ id, title, subtitle, as: Heading = 'h2', className, children }) {
  return (
    <header className={cx('card__head', className)}>
      <Heading className="card__title" id={id}>
        {title}
      </Heading>
      {subtitle && <p className="card__sub">{subtitle}</p>}
      {children}
    </header>
  );
}
