import { cx } from '@/lib/format';

/**
 * Tinted notice.
 *
 * @param {'banner'|'card'} variant `banner` adds spacing below; `card` is the prominent failure style.
 * @param {string} role ARIA live role ("status" or "alert").
 * @param {string} tone Optional modifier class applied to the title and text (e.g. "text-link").
 * @param {node} emphasis Extra line shown in the warning colour (card variant).
 */
export default function Alert({ id, title, children, variant, role, tone, emphasis }) {
  const spaced = variant === 'banner' || variant === 'card';
  return (
    <section
      className={cx('alert', variant === 'card' && 'alert--card', spaced && 'alert--banner')}
      role={role}
      aria-labelledby={id}
    >
      <h2 className={cx('alert__title', tone)} id={id}>
        {title}
      </h2>
      {children && <p className={cx('alert__text', tone)}>{children}</p>}
      {emphasis && <p className="alert__emphasis">{emphasis}</p>}
    </section>
  );
}
