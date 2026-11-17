'use client';

import Link from 'next/link';
import { Dropdown, Menu } from 'antd';
import { DownOutlined, PlusOutlined } from '@ant-design/icons';
import Avatar from '@/components/ui/Avatar';
import { NAV_ITEMS, activePath } from '@/config/navigation';
import { roleLabel } from '@/config/roles';
import { can } from '@/lib/permissions';

function visible(items, user) {
  return items
    .filter((item) => can(user, item.permission))
    .map((item) => (item.children ? { ...item, children: visible(item.children, user) } : item))
    .filter((item) => !item.children || item.children.length > 0);
}

function toMenu(items) {
  return items.map((item) =>
    item.children
      ? { key: item.id, label: item.label, popupClassName: 'nav-popup', children: toMenu(item.children) }
      : { key: item.id, label: <Link href={item.href}>{item.label}</Link> },
  );
}

/**
 * The top header, in the style of Apache Superset: brand, the main menu, a "+" menu for
 * new charts and dashboards, the data refresh time and the user menu.
 */
export default function Header({ active, user, refreshed }) {
  const selected = activePath(active);
  const items = toMenu(visible(NAV_ITEMS, user));
  const canBuild = can(user, 'reports:manage');

  const createItems = [
    { key: 'chart', label: <Link href="/explore">Chart</Link> },
    { key: 'dashboard', label: <Link href="/dashboards?new=1">Dashboard</Link> },
  ];

  const userItems = user
    ? [
        {
          key: 'who',
          type: 'group',
          label: (
            <span className="header__menu-who">
              {user.email} · {roleLabel(user.role)}
            </span>
          ),
        },
        { key: 'account', label: <Link href="/account">My account</Link> },
        { type: 'divider' },
        {
          key: 'signout',
          label: (
            <form action="/auth/sign-out" method="post">
              <button className="header__menu-button" type="submit">
                Sign out
              </button>
            </form>
          ),
        },
      ]
    : [];

  return (
    <header className="header">
      <Link className="header__brand" href="/dashboards" aria-label="iHub Analytics home">
        <svg className="header__mark" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="12" width="4" height="9" />
          <rect x="10" y="7" width="4" height="14" />
          <rect x="17" y="3" width="4" height="18" />
        </svg>
        <span className="header__name">iHub</span>
      </Link>

      <Menu className="header__menu" mode="horizontal" selectedKeys={selected} items={items} disabledOverflow />

      <div className="header__right">
        {refreshed && (
          <span className="header__refreshed" title="When the data was last rebuilt">
            Data refreshed {refreshed}
          </span>
        )}
        {canBuild && (
          <Dropdown menu={{ items: createItems }} placement="bottomRight" trigger={['click']}>
            <button className="header__icon-button" type="button" aria-label="Create a chart or dashboard">
              <PlusOutlined />
            </button>
          </Dropdown>
        )}
        {user && (
          <Dropdown menu={{ items: userItems }} placement="bottomRight" trigger={['click']}>
            <button className="header__user" type="button" aria-label="Account menu">
              <Avatar user={user} />
              <span className="header__user-name">{user.name || user.email}</span>
              <DownOutlined className="header__caret" />
            </button>
          </Dropdown>
        )}
      </div>
    </header>
  );
}
