import { apiServer } from '@/lib/api/server';
import { InvitesTable, type InviteRow } from '@/components/admin/InvitesTable';
import { InviteDialog } from '@/components/admin/InviteDialog';

interface InvitesListOut {
  invites: InviteRow[];
}

export default async function AdminInvitesPage() {
  const list = await apiServer<InvitesListOut>('/api/admin/invites');

  const now = Date.now();
  const activeCount = list.invites.filter(
    (i) => !i.used_at && new Date(i.expires_at).getTime() >= now,
  ).length;
  const usedCount = list.invites.filter((i) => !!i.used_at).length;

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · II.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Приглашения<br />
            <span className="italic">портала.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Выданные приглашения для регистрации новых пользователей. Активные
            ссылки можно скопировать и&nbsp;отправить адресату. Просроченные
            и&nbsp;использованные приглашения остаются в&nbsp;истории.
          </p>
        </div>
        <div className="flex flex-col items-start justify-end gap-3 md:items-end">
          <div className="flex items-baseline gap-6">
            <Stat n={activeCount} label="активных" accent />
            <Stat n={usedCount} label="принято" />
            <Stat n={list.invites.length} label="всего" />
          </div>
          <InviteDialog />
        </div>
      </div>

      <div className="ed-anim-rise ed-d-2">
        <InvitesTable invites={list.invites} />
      </div>
    </div>
  );
}

function Stat({ n, label, accent }: { n: number; label: string; accent?: boolean }) {
  return (
    <div className="text-right">
      <div
        className={`font-serif text-4xl font-bold tabular-nums ${
          accent
            ? 'text-[color:var(--color-accent)]'
            : 'text-[color:var(--color-text-primary)]'
        }`}
      >
        {n}
      </div>
      <div className="ed-eyebrow">{label}</div>
    </div>
  );
}
