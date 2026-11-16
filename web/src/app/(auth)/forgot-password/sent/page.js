import AuthPage from '@/components/auth/AuthPage';
import Countdown from '@/components/auth/Countdown';
import Button from '@/components/ui/Button';

export const metadata = {
  title: 'Check your inbox',
  description: 'A password reset link has been sent if an account exists for the address.',
};

export default function ResetLinkSentPage() {
  return (
    <AuthPage title="Check your inbox" lead="A password reset link is on its way." tall>
      <div className="auth-form auth-form--loose">
        <p className="auth-form__body mt-12">
          If an account exists for this address, you’ll receive a link to reset your password.
        </p>
        <p className="auth-form__body-strong">name@organisation.org</p>
        <p className="auth-form__fine">Check spam folders. The link expires in 30 minutes.</p>
        <Button className="mt-12" href="/login">
          Back to sign in
        </Button>
        <p className="auth-form__fine" role="status">
          <Countdown seconds={30} template="Resend link in {t}s" done="You can request a new link now." />
        </p>
      </div>
    </AuthPage>
  );
}
