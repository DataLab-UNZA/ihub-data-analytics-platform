import AuthPage from '@/components/auth/AuthPage';
import Button from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Form';

export const metadata = {
  title: 'Join your organisation',
  description: 'Accept your invitation to the University of Zambia workspace.',
};

export default function AcceptInvitationPage() {
  return (
    <AuthPage title="Join your organisation" lead="You’re invited to the University of Zambia." tall>
      <form className="auth-form" action="/choose-workspace" method="get">
        <Field id="full-name" label="Full name">
          <Input
            id="full-name"
            name="full-name"
            type="text"
            placeholder="Enter your full name"
            autoComplete="name"
            required
          />
        </Field>
        <Field id="create-password" label="Create password">
          <Input
            id="create-password"
            name="password"
            type="password"
            placeholder="At least 12 characters"
            minLength={12}
            autoComplete="new-password"
            required
          />
        </Field>
        <p className="auth-form__fine">Role: Analyst · invited by Workspace admin</p>
        <p className="auth-form__fine">
          By continuing, you accept the <a href="#terms">terms of use</a>.
        </p>
        <Button type="submit">Accept invitation</Button>
      </form>
    </AuthPage>
  );
}
