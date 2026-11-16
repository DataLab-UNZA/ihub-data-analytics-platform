import NotificationCenter from '@/components/features/notifications/NotificationCenter';
import PageHeader from '@/components/layout/PageHeader';
import { notificationTabs, notifications } from '@/data/workspace';

export const metadata = {
  title: 'Notifications',
  description: 'Source alerts, report completions, corrections and workspace invitations.',
};

export default function NotificationsPage() {
  return (
    <>
      <PageHeader title="Notifications" aside="Illustrative data · not connected yet" />
      <NotificationCenter items={notifications} tabs={notificationTabs} />
    </>
  );
}
