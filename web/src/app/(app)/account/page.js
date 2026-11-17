import { cookies } from 'next/headers';
import PageHeader from '@/components/layout/PageHeader';
import OtpInput from '@/components/auth/OtpInput';
import Avatar from '@/components/ui/Avatar';
import Card, { CardHeader } from '@/components/ui/Card';
import { Field, Input } from '@/components/ui/Form';
import { roleLabel } from '@/config/roles';
import { currentUser } from '@/lib/api';
import { EMAIL_CHANGE_COOKIE, FLASH_COOKIE, readFlash } from '@/lib/session';

export const metadata = {
  title: 'My account',
  description: 'Your profile photo, name, phone, email address and access.',
};

const DATE = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

/** Your own account (ADR-010): photo, details, a confirmed email change, and your access. */
export default async function AccountPage() {
  const store = await cookies();
  const [user, flash] = [await currentUser(), readFlash(store.get(FLASH_COOKIE)?.value)];
  const pendingEmail = store.get(EMAIL_CHANGE_COOKIE)?.value;

  if (!user) {
    return (
      <>
        <PageHeader title="My account" filters={false} />
        <Card aria-labelledby="account-off">
          <CardHeader id="account-off" title="Sign-in is off here" subtitle="Accounts appear when sign-in is switched on." />
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader title="My account" filters={false} />
      {flash && (
        <p className={flash.kind === 'info' ? 'notice mb-24' : 'notice notice--error mb-24'} role={flash.kind === 'info' ? 'status' : 'alert'}>
          {flash.message}
        </p>
      )}

      <div className="grid grid--main-aside">
        <div className="stack stack--md">
          <Card aria-labelledby="photo-title">
            <CardHeader id="photo-title" title="Profile photo" subtitle="PNG, JPEG or WebP, up to 2 MB. Shown in the top bar." />
            <div className="account-photo">
              <Avatar user={user} size="lg" />
              <div className="stack stack--sm">
                <form className="account-photo__upload" action="/account-actions/avatar" method="post" encType="multipart/form-data">
                  <label className="sr-only" htmlFor="photo">
                    Choose a photo
                  </label>
                  <input className="input" id="photo" name="photo" type="file" accept="image/png,image/jpeg,image/webp" required />
                  <button className="btn btn--sm" type="submit">
                    Upload photo
                  </button>
                </form>
                {user.avatar_updated_at && (
                  <form action="/account-actions/avatar" method="post">
                    <input type="hidden" name="remove" value="1" />
                    <button className="btn btn--secondary btn--compact" type="submit">
                      Remove photo
                    </button>
                  </form>
                )}
              </div>
            </div>
          </Card>

          <Card aria-labelledby="details-title">
            <CardHeader id="details-title" title="Personal details" subtitle="How you appear to administrators and in the top bar." />
            <form className="stack stack--md" action="/account-actions/profile" method="post">
              <Field id="name" label="Full name">
                <Input id="name" name="name" defaultValue={user.name ?? ''} autoComplete="name" maxLength={100} />
              </Field>
              <Field id="phone" label="Phone number" hint="International format, for example +260 97 123 4567.">
                <Input id="phone" name="phone" type="tel" defaultValue={user.phone ?? ''} autoComplete="tel" maxLength={30} />
              </Field>
              <button className="btn" type="submit">
                Save details
              </button>
            </form>
          </Card>

          <Card id="email" aria-labelledby="email-title">
            <CardHeader
              id="email-title"
              title="Email address"
              subtitle="Used to sign in. A new address must be confirmed with a code sent to it."
            />
            <p className="account-email">
              <span className="text-muted">Current</span> <strong>{user.email}</strong>
            </p>
            {pendingEmail ? (
              <>
                <form className="stack stack--md" action="/account-actions/email/verify" method="post">
                  <p>
                    Enter the 6-digit code sent to <strong>{pendingEmail}</strong>.
                  </p>
                  <OtpInput />
                  <button className="btn" type="submit">
                    Confirm new email
                  </button>
                </form>
                <form className="mt-12" action="/account-actions/email/cancel" method="post">
                  <button className="btn btn--secondary btn--compact" type="submit">
                    Cancel the change
                  </button>
                </form>
              </>
            ) : (
              <form className="stack stack--md" action="/account-actions/email" method="post">
                <Field id="new-email" label="New email address">
                  <Input id="new-email" name="email" type="email" autoComplete="email" required />
                </Field>
                <button className="btn btn--secondary" type="submit">
                  Send confirmation code
                </button>
              </form>
            )}
          </Card>
        </div>

        <Card as="aside" aria-labelledby="access-title">
          <CardHeader id="access-title" title="Access" subtitle="Your role is set by an administrator." />
          <dl className="account-facts">
            <dt>Role</dt>
            <dd>{roleLabel(user.role)}</dd>
            <dt>Permissions</dt>
            <dd>
              <ul className="account-permissions">
                {user.permissions.map((permission) => (
                  <li key={permission}>{permission}</li>
                ))}
              </ul>
            </dd>
            <dt>Member since</dt>
            <dd>{DATE.format(new Date(user.created_at))}</dd>
            {user.last_sign_in_at && (
              <>
                <dt>Last sign-in</dt>
                <dd>{DATE.format(new Date(user.last_sign_in_at))}</dd>
              </>
            )}
          </dl>
          <form className="mt-24" action="/auth/sign-out" method="post">
            <button className="btn btn--secondary btn--block" type="submit">
              Sign out
            </button>
          </form>
        </Card>
      </div>
    </>
  );
}
