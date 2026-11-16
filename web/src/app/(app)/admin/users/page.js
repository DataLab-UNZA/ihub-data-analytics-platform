import PageHeader from '@/components/layout/PageHeader';
import Button from '@/components/ui/Button';
import Card, { CardHeader } from '@/components/ui/Card';
import DataTable from '@/components/ui/DataTable';
import { rolePermissions, workspaceUsers } from '@/data/admin';

export const metadata = {
  title: 'Users & roles',
  description: 'Workspace access, invitations and the visibility rules for each role.',
};

const USER_COLUMNS = [
  { key: 'user', header: 'User', rowHeader: true, href: () => '/admin/users' },
  { key: 'role', header: 'Role' },
  { key: 'scope', header: 'Scope' },
  { key: 'status', header: 'Status' },
];

const ROLE_COLUMNS = [
  { key: 'role', header: 'Role', rowHeader: true, href: () => '/admin/users' },
  { key: 'scope', header: 'Data scope' },
  { key: 'individual', header: 'Individual records' },
  { key: 'manage', header: 'Manage' },
];

export default function UsersPage() {
  return (
    <>
      <PageHeader title="Users & roles" />

      <Card className="mb-24" aria-labelledby="access-title">
        <CardHeader id="access-title" title="Workspace access" subtitle="People and invitations · names are illustrative" />
        <DataTable
          caption="People with access to this workspace"
          columns={USER_COLUMNS}
          rows={workspaceUsers}
          variant="roomy"
        />
        <div className="align-end mt-16">
          <Button size="sm" href="/accept-invitation">
            Invite user
          </Button>
        </div>
      </Card>

      <Card aria-labelledby="roles-title">
        <CardHeader
          id="roles-title"
          title="Roles & visibility"
          subtitle="Individual views require explicit authorisation · exports inherit the same permissions"
        />
        <DataTable
          caption="Data scope and permissions for each role"
          columns={ROLE_COLUMNS}
          rows={rolePermissions}
          variant="compact"
        />
      </Card>
    </>
  );
}
