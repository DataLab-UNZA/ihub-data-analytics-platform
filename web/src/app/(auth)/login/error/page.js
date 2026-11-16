import LoginScreen from '@/components/auth/LoginScreen';

export const metadata = {
  title: 'Sign in (error)',
  description: 'Sign-in form showing an incorrect email or password message.',
};

export default function LoginErrorPage() {
  return <LoginScreen variant="error" />;
}
