import Link from 'next/link';
import { cx } from '@/lib/format';

/**
 * Button or link styled as a button.
 *
 * Renders a Next.js <Link> when `href` is given, otherwise a <button>.
 *
 * @param {'primary'|'secondary'} variant Visual style.
 * @param {'sm'|'md'|'lg'} size Minimum width.
 * @param {boolean} block Stretch to the container width.
 */
export default function Button({
  href,
  variant = 'primary',
  size,
  block = false,
  className,
  children,
  type = 'button',
  ...props
}) {
  const classes = cx(
    'btn',
    variant === 'secondary' && 'btn--secondary',
    size && `btn--${size}`,
    block && 'btn--block',
    className,
  );

  if (href) {
    return (
      <Link className={classes} href={href} {...props}>
        {children}
      </Link>
    );
  }

  return (
    <button className={classes} type={type} {...props}>
      {children}
    </button>
  );
}
