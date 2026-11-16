import LoginScreen from '@/components/auth/LoginScreen';

export const metadata = {
  title: 'Session expired',
  description: 'Your session expired. Sign in again to keep your data secure.',
};

export default function SessionExpiredPage() {
  return <LoginScreen variant="expired" />;
}
