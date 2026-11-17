import { redirect } from 'next/navigation';
import { currentUser } from '@/lib/api';
import { can } from '@/lib/permissions';
import { signInRequired } from '@/lib/session';

/**
 * Administration needs the users:manage permission (ADR-010). Checked on the server before
 * any admin page renders; the API checks it again on every admin call.
 */
export default async function AdminLayout({ children }) {
  if (signInRequired()) {
    const user = await currentUser();
    if (!user || !can(user, 'users:manage')) {
      redirect('/access-restricted');
    }
  }
  return children;
}
