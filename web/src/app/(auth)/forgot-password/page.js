import Link from 'next/link';
import AuthPage from '@/components/auth/AuthPage';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';

export const metadata = {
  title: 'Forgot password',
  description: 'Request a secure link to reset your iHub Analytics password.',
};

export default function ForgotPasswordPage() {
  return (
    <AuthPage title="Forgot password?" lead="We’ll send you a secure reset link." tall>
      <form className="auth-form auth-form--loose" action="/forgot-password/sent" method="get">
        <Field id="email" label="Work email">
          <Input
            id="email"
            name="email"
            type="email"
            placeholder="name@organisation.org"
            autoComplete="username"
            required
          />
        </Field>
        <Button type="submit">Send reset link</Button>
        <p className="auth-form__fine">Reset links expire after 30 minutes.</p>
        <p>
          <Link href="/login">Back to sign in</Link>
        </p>
      </form>
    </AuthPage>
  );
}
