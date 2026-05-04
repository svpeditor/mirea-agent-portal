import { apiServer } from '@/lib/api/server';
import { ApiError, type UserOut } from '@/lib/api/types';
import { UsersTable } from '@/components/admin/UsersTable';
import { UserDrawer } from '@/components/admin/UserDrawer';
import { InviteDialog } from '@/components/admin/InviteDialog';

interface UsersListOut {
  users: UserOut[];
  next_cursor: string | null;
}

interface UserAdminOut extends UserOut {
  quota: {
    monthly_limit_usd: string;
    period_used_usd: string;
    per_job_cap_usd: string;
    period_starts_at: string;
  } | null;
}

export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<{ drawer?: string }>;
}) {
  const { drawer } = await searchParams;
  const list = await apiServer<UsersListOut>('/api/admin/users');

  let selectedUser: UserAdminOut | null = null;
  if (drawer) {
    try {
      selectedUser = await apiServer<UserAdminOut>(`/api/admin/users/${drawer}`);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) throw err;
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-serif text-3xl">Пользователи</h1>
        <InviteDialog />
      </div>

      <UsersTable users={list.users} />

      <UserDrawer user={selectedUser} />
    </div>
  );
}
