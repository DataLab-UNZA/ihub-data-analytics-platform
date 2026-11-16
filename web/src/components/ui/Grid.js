import { cx } from '@/lib/format';

/**
 * Responsive CSS grid.
 *
 * @param {'kpi'|'halves'|'thirds'|'main-aside'|'wide-narrow'|'trio'} variant Column layout.
 * @param {boolean} start Align items to the top instead of stretching them.
 */
export default function Grid({ variant, start = false, as: Tag = 'div', className, children, ...props }) {
  return (
    <Tag className={cx('grid', variant && `grid--${variant}`, start && 'grid--start', className)} {...props}>
      {children}
    </Tag>
  );
}

/** Vertical stack of cards inside one grid column. */
export function GridStack({ children }) {
  return <div className="grid__stack">{children}</div>;
}
