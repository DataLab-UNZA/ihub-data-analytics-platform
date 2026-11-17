import { cookies } from 'next/headers';
import PageHeader from '@/components/layout/PageHeader';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { ROLES, roleLabel } from '@/config/roles';
import { rolePermissions, workspaceUsers } from '@/data/admin';
import { apiGet, currentUser } from '@/lib/api';
import { FLASH_COOKIE, readFlash, signInRequired } from '@/lib/session';

export const metadata = {
  title: 'Users & roles',
  description: 'Who can sign in, their roles, and what each role may do.',
};

const DATE = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

function RoleForm({ user, self }) {
  return (
    <form className="inline-form" action={`/admin-actions/users/${user.id}`} method="post">
      <label className="sr-only" htmlFor={`role-${user.id}`}>
        Role for {user.email}
      </label>
      <select className="select-plain" id={`role-${user.id}`} name="role" defaultValue={user.role} disabled={self}>
        {ROLES.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {!self && (
        <button className="btn btn--secondary btn--compact" type="submit">
          Save
        </button>
      )}
    </form>
  );
}

function StatusForm({ user, self }) {
  if (self) {
    return 'Active (you)';
  }
  const next = user.status === 'active' ? 'deactivated' : 'active';
  return (
    <form className="inline-form" action={`/admin-actions/users/${user.id}`} method="post">
      <input type="hidden" name="status" value={next} />
      <span>{user.status === 'active' ? 'Active' : 'Deactivated'}</span>
      <button className="btn btn--secondary btn--compact" type="submit">
        {next === 'active' ? 'Reactivate' : 'Deactivate'}
      </button>
    </form>
  );
}

/** Users & roles: real accounts from the API when sign-in is on (ADR-010). */
export default async function UsersPage() {
  if (!signInRequired()) {
    return <IllustrativeUsers />;
  }
  const [me, users, roles, flash] = await Promise.all([
    currentUser(),
    apiGet('/api/admin/users'),
    apiGet('/api/admin/roles'),
    cookies().then((store) => readFlash(store.get(FLASH_COOKIE)?.value)),
  ]);

  const userColumns = [
    { key: 'email', header: 'User', rowHeader: true, render: (u) => (u.name ? `${u.name} · ${u.email}` : u.email) },
    { key: 'role', header: 'Role', render: (u) => <RoleForm user={u} self={u.id === me?.id} /> },
    { key: 'status', header: 'Status', render: (u) => <StatusForm user={u} self={u.id === me?.id} /> },
    {
      key: 'last',
      header: 'Last sign-in',
      render: (u) => (u.last_sign_in_at ? DATE.format(new Date(u.last_sign_in_at)) : '—'),
    },
  ];
  const roleColumns = [
    { key: 'role', header: 'Role', rowHeader: true, render: (r) => roleLabel(r.role) },
    { key: 'permissions', header: 'Permissions', render: (r) => r.permissions.join(', ') },
  ];

  return (
    <>
      <PageHeader title="Users & roles" filters={false} />
      {flash && (
        <p className={flash.kind === 'info' ? 'notice mb-16' : 'notice notice--error mb-16'} role={flash.kind === 'info' ? 'status' : 'alert'}>
          {flash.message}
        </p>
      )}
      <Card className="mb-24" aria-labelledby="access-title">
        <CardHeader
          id="access-title"
          title="People who can sign in"
          subtitle="Anyone allowed signs up by signing in; new accounts start as Member. You cannot change your own access."
        />
        <DataTable caption="Users and their roles" columns={userColumns} rows={users} variant="roomy" />
      </Card>
      <Card aria-labelledby="roles-title">
        <CardHeader id="roles-title" title="Roles and permissions" subtitle="The API enforces these on every request" />
        <DataTable
          caption="What each role may do"
          columns={roleColumns}
          rows={roles.map((r) => ({ ...r, id: r.role }))}
          variant="compact"
        />
      </Card>
    </>
  );
}

/** The design's illustrative table, shown while sign-in is switched off. */
function IllustrativeUsers() {
  const columns = [
    { key: 'user', header: 'User', rowHeader: true },
    { key: 'role', header: 'Role' },
    { key: 'scope', header: 'Scope' },
    { key: 'status', header: 'Status' },
  ];
  const roleColumns = [
    { key: 'role', header: 'Role', rowHeader: true },
    { key: 'scope', header: 'Data scope' },
    { key: 'individual', header: 'Individual records' },
    { key: 'manage', header: 'Manage' },
  ];
  return (
    <>
      <PageHeader title="Users & roles" filters={false} />
      <Card className="mb-24" aria-labelledby="access-title">
        <CardHeader id="access-title" title="Workspace access" subtitle="Sign-in is off here · names are illustrative" />
        <DataTable caption="People with access to this workspace" columns={columns} rows={workspaceUsers} variant="roomy" />
      </Card>
      <Card aria-labelledby="roles-title">
        <CardHeader id="roles-title" title="Roles & visibility" subtitle="Illustrative" />
        <DataTable caption="Data scope and permissions for each role" columns={roleColumns} rows={rolePermissions} variant="compact" />
      </Card>
    </>
  );
}
