import { cookies } from 'next/headers';
import { cx } from '@/lib/format';
import { FLASH_COOKIE, readFlash } from '@/lib/session';

/** The one-off message a sign-in route left for this screen (error or information). */
export default async function FlashMessage() {
  const flash = readFlash((await cookies()).get(FLASH_COOKIE)?.value);
  if (!flash) {
    return null;
  }
  const isError = flash.kind !== 'info';
  return (
    <p
      className={cx('auth-form__status', isError && 'auth-form__status--error')}
      id="auth-status"
      role={isError ? 'alert' : 'status'}
    >
      {flash.message}
    </p>
  );
}
