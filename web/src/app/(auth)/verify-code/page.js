import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import Link from 'next/link';
import AuthPage from '@/components/auth/AuthPage';
import FlashMessage from '@/components/auth/FlashMessage';
import OtpInput from '@/components/auth/OtpInput';
import Button from '@/components/ui/Button';
import { PENDING_COOKIE, readPending } from '@/lib/session';

export const metadata = {
  title: 'Check your email',
  description: 'Enter the six-digit code sent to your email to finish signing in.',
};

/** Shows "t*****@gmail.com": enough to recognise the address, not to read it over a shoulder. */
function masked(email) {
  const [local, domain] = email.split('@');
  return `${local.slice(0, 1)}${'*'.repeat(Math.max(1, local.length - 1))}@${domain}`;
}

/** Email sign-in, step 2: type the code from the email (ADR-010). */
export default async function VerifyCodePage() {
  const pending = readPending((await cookies()).get(PENDING_COOKIE)?.value);
  if (!pending) {
    redirect('/login');
  }

  return (
    <AuthPage title="Check your email" lead="Enter the 6-digit code we sent you." headClassName="mb-20" tall>
      <form className="auth-form" action="/auth/email/verify" method="post">
        <p className="auth-form__email">{masked(pending.email)}</p>
        <FlashMessage />
        <OtpInput />
        <Button className="mt-12" type="submit">
          Verify &amp; continue
        </Button>
        <p className="auth-form__fine">The code expires after 10 minutes and works once.</p>
      </form>
      <form className="auth-form" action="/auth/email/resend" method="post">
        <Button type="submit" variant="secondary" block>
          Send a new code
        </Button>
        <p>
          <Link href="/login">Use a different email</Link>
        </p>
      </form>
    </AuthPage>
  );
}
