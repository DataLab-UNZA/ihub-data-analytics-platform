import { cx } from '@/lib/format';

/** Up to two initials from the name, or the first letter of the email. */
export function initials(user) {
  const source = (user?.name || user?.email || '?').trim();
  const words = source.includes('@') ? [source] : source.split(/\s+/);
  return words
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('');
}

/**
 * The signed-in user's photo, or their initials when there is none.
 * The photo comes from /me/avatar (streamed with the user's token); `avatar_updated_at`
 * is added to the URL so a new upload shows at once.
 *
 * @param {'sm'|'lg'} size Small for the top bar, large for the account page.
 */
export default function Avatar({ user, size = 'sm', className }) {
  const classes = cx('avatar', `avatar--${size}`, className);
  if (user?.avatar_updated_at) {
    const version = encodeURIComponent(user.avatar_updated_at);
    // eslint-disable-next-line @next/next/no-img-element -- a private, per-user image, not a static asset
    return <img className={classes} src={`/me/avatar?v=${version}`} alt="" />;
  }
  return (
    <span className={classes} aria-hidden="true">
      {initials(user)}
    </span>
  );
}
