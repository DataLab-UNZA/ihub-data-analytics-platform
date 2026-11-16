import Link from 'next/link';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';
import { cx } from '@/lib/format';
import AuthPage from './AuthPage';

const VARIANTS = {
  default: {
    title: 'Welcome back',
    lead: 'Please enter your details',
    center: true,
    password: 'demo-password',
    status: '',
  },
  error: {
    title: 'Welcome back',
    lead: 'Please enter your details',
    center: true,
    password: 'wrong-password',
    status: 'Email or password is incorrect. Try again.',
    invalid: true,
  },
  expired: {
    title: 'Your session expired',
    lead: 'Sign in again to keep your data secure.',
    center: false,
    password: 'demo-password',
    status: 'Your previous filters have been kept.',
  },
};

/**
 * Sign-in form shared by the default, error and session-expired screens.
 * The demo credentials only mirror the supplied designs.
 *
 * @param {'default'|'error'|'expired'} variant
 */
export default function LoginScreen({ variant = 'default' }) {
  const config = VARIANTS[variant];
  const describedBy = config.invalid ? 'login-error' : undefined;

  return (
    <AuthPage title={config.title} lead={config.lead} center={config.center}>
      <form className="auth-form" action="/verify-code" method="get">
        <Field id="email" label="Work email">
          <Input
            id="email"
            name="email"
            type="email"
            defaultValue="executive@unza.zm"
            autoComplete="username"
            aria-invalid={config.invalid || undefined}
            aria-describedby={describedBy}
            required
          />
        </Field>
        <Field id="password" label="Password">
          <Input
            id="password"
            name="password"
            type="password"
            defaultValue={config.password}
            autoComplete="current-password"
            aria-invalid={config.invalid || undefined}
            aria-describedby={describedBy}
            required
          />
        </Field>
        <p className="auth-form__aux">
          <Link href="/forgot-password">Forgot password?</Link>
        </p>
        <p
          className={cx('auth-form__status', config.invalid && 'auth-form__status--error')}
          id={config.invalid ? 'login-error' : undefined}
          role={config.invalid ? 'alert' : 'status'}
        >
          {config.status}
        </p>
        <Button type="submit">Sign in</Button>
        <p className="auth-form__divider">or</p>
        <Button href="/choose-workspace" variant="secondary">
          Continue with SSO
        </Button>
        <p className="auth-form__fine">Use your organisation’s identity provider</p>
      </form>
    </AuthPage>
  );
}
