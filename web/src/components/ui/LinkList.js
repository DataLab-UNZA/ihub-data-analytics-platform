import Link from 'next/link';
import { cx } from '@/lib/format';

/** Divided list of links with an optional description line under each. */
export default function LinkList({ items, divided = false, roomy = false }) {
  return (
    <ul className={cx('link-list', divided && 'link-list--divided', roomy && 'link-list--roomy')}>
      {items.map((item) => (
        <li key={item.label}>{item.children ?? <Link href={item.href}>{item.label}</Link>}</li>
      ))}
    </ul>
  );
}
