import { apiServer } from '@/lib/api/server';
import { ApiError, type UserOut } from '@/lib/api/types';
import { UsersTable } from '@/components/admin/UsersTable';
import { UserDrawer } from '@/components/admin/UserDrawer';
import { InviteDialog } from '@/components/admin/InviteDialog';
import { requireAdmin } from '@/lib/auth/current-user';

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
  const [list, usage, me] = await Promise.all([
    apiServer<UsersListOut>('/api/admin/users'),
    apiServer<{
      by_user: Array<{ user_id: string; email: string; cost_usd: string; requests: number }>;
    }>('/api/admin/usage').catch(() => ({ by_user: [] })),
    requireAdmin(),
  ]);

  const costByUserId: Record<string, string> = {};
  const requestsByUserId: Record<string, number> = {};
  for (const row of usage.by_user) {
    costByUserId[row.user_id] = row.cost_usd;
    requestsByUserId[row.user_id] = row.requests;
  }

  let selectedUser: UserAdminOut | null = null;
  if (drawer) {
    try {
      selectedUser = await apiServer<UserAdminOut>(`/api/admin/users/${drawer}`);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) throw err;
    }
  }

  const adminCount = list.users.filter((u) => u.role === 'admin').length;

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · I.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Подписчики<br />
            <span className="italic">портала.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Все зарегистрированные пользователи. Включает преподавателей-членов
            НУГ, студентов-разработчиков и&nbsp;администраторов.
          </p>
        </div>
        <div className="flex flex-col items-start justify-end gap-3 md:items-end">
          <div className="flex items-baseline gap-6">
            <Stat n={list.users.length} label="всего" />
            <Stat n={adminCount} label="админов" accent />
          </div>
          <InviteDialog />
        </div>
      </div>

      <div className="ed-anim-rise ed-d-2">
        <UsersTable
          users={list.users}
          costByUserId={costByUserId}
          requestsByUserId={requestsByUserId}
        />
      </div>

      <UserDrawer user={selectedUser} currentUserId={me.id} />
    </div>
  );
}

function Stat({ n, label, accent }: { n: number; label: string; accent?: boolean }) {
  return (
    <div className="text-right">
      <div
        className={`font-serif text-4xl font-bold tabular-nums ${
          accent ? 'text-[color:var(--color-accent)]' : 'text-[color:var(--color-text-primary)]'
        }`}
      >
        {n}
      </div>
      <div className="ed-eyebrow">{label}</div>
    </div>
  );
}
