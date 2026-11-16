import { cx } from '@/lib/format';
import Card, { CardHeader } from './Card';

/**
 * Full-width card for empty, error and restricted states.
 *
 * @param {boolean} short Use the compact variant (empty and error states).
 * @param {string} subtitle When present the heading is rendered as a card header with a sub-line.
 */
export default function StateCard({ id, title, subtitle, short = false, role, children }) {
  return (
    <Card className={cx('state', short && 'state--short')} aria-labelledby={id} role={role}>
      {subtitle ? (
        <CardHeader id={id} title={title} subtitle={subtitle} />
      ) : (
        <h2 className="card__title" id={id}>
          {title}
        </h2>
      )}
      <div className="state__body">{children}</div>
    </Card>
  );
}
