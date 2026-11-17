import AuthPage from '@/components/auth/AuthPage';
import FlashMessage from '@/components/auth/FlashMessage';
import { Field, Input } from '@/components/ui/Form';
import { apiPublicGet } from '@/lib/api';
import { safeNext } from '@/lib/session';

export const metadata = {
  title: 'Sign in',
  description: 'Sign in to iHub Analytics with Google or with a code sent to your email.',
};

async function signInMethods() {
  const result = await apiPublicGet('/api/auth/methods');
  return result.ok ? result.data : { unavailable: result.data?.detail ?? 'Sign-in is not available.' };
}

/** Google's "G", as its sign-in branding guidelines ask for on a "Sign in with Google" button. */
function GoogleMark() {
  return (
    <svg className="btn__icon" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  );
}

/**
 * Sign-in screen (ADR-010): a one-time code by email, or Google. Both run through route
 * handlers under /auth/*, which keep the tokens in httpOnly cookies.
 */
export default async function LoginPage({ searchParams }) {
  const next = safeNext((await searchParams)?.next);
  const methods = await signInMethods();
  const domain = methods.allowed_domain;
  const anyDomain = domain === '*' || !domain;

  return (
    <AuthPage
      title="Welcome back!"
      lead={anyDomain ? 'Sign in to see your research analytics.' : `Sign in with your @${domain} account.`}
      footer={
        <>
          New here? <strong>Your first sign-in creates your account.</strong>
        </>
      }
    >
      <div className="auth-form">
        <FlashMessage />
        {methods.unavailable && (
          <p className="auth-form__status auth-form__status--error" role="alert">
            {methods.unavailable}
          </p>
        )}

        {methods.email_code && (
          <form className="auth-form" action="/auth/email" method="post">
            <input type="hidden" name="next" value={next} />
            <Field id="email" label="Email">
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder={anyDomain ? 'Enter your email' : `name@${domain}`}
                required
              />
            </Field>
            <button className="btn btn--block" type="submit">
              Email me a sign-in code
            </button>
            <p className="auth-form__fine">No password: we email you a 6-digit code.</p>
          </form>
        )}

        {methods.google && methods.email_code && <p className="auth-form__divider">or</p>}

        {methods.google && (
          // A plain link, not <Link>: the route handler redirects the browser to Google.
          <a className="btn btn--secondary btn--block btn--google" href={`/auth/google?next=${encodeURIComponent(next)}`}>
            <GoogleMark />
            Sign in with Google
          </a>
        )}
      </div>
    </AuthPage>
  );
}
