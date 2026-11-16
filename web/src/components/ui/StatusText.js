import { cx } from '@/lib/format';

/** Small coloured status line ("ok" green, "warn" amber). */
export default function StatusText({ tone = 'ok', className, children, ...props }) {
  return (
    <p className={cx('status-text', `status-text--${tone}`, className)} {...props}>
      {children}
    </p>
  );
}
