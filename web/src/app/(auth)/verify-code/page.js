import Link from 'next/link';
import AuthPage from '@/components/auth/AuthPage';
import Countdown from '@/components/auth/Countdown';
import OtpInput from '@/components/auth/OtpInput';
import Button from '@/components/ui/Button';

export const metadata = {
  title: 'Check your email',
  description: 'Enter the six-digit code sent to your work email to finish signing in.',
};

export default function VerifyCodePage() {
  return (
    <AuthPage
      title="Check your email"
      lead="Enter the 6-digit code sent to your work email."
      headClassName="mb-20"
      tall
    >
      <form className="auth-form" action="/choose-workspace" method="get">
        <p className="auth-form__email">executive@unza.zm</p>
        <OtpInput defaultValue="2481" />
        <p className="auth-form__fine">
          <Countdown
            seconds={582}
            format="clock"
            template="Code expires in {t}"
            done="This code has expired. Request a new one."
          />
        </p>
        <Button className="mt-12" type="submit">
          Verify &amp; continue
        </Button>
        <p className="auth-form__fine">
          <Countdown seconds={30} template="Resend code in {t}s" done="You can request a new code now." />
        </p>
        <p>
          <Link href="/verify-code">Use a recovery code</Link>
        </p>
      </form>
    </AuthPage>
  );
}
