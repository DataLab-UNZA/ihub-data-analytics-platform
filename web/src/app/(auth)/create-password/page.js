import AuthPage from '@/components/auth/AuthPage';
import CreatePasswordForm from '@/components/auth/CreatePasswordForm';

export const metadata = {
  title: 'Create a password',
  description: 'Choose a new password of at least 12 characters.',
};

export default function CreatePasswordPage() {
  return (
    <AuthPage title="Create a password" lead="Use at least 12 characters." leadId="password-hint" tall>
      <CreatePasswordForm defaultPassword="a-long-passphrase" />
    </AuthPage>
  );
}
