import { apiServer } from '@/lib/api/server';
import { formatDate } from '@/lib/format';

interface AuditLogOut {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  payload: Record<string, unknown>;
  ip: string | null;
  user_agent: string | null;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  'invite.create': 'выдано приглашение',
  'invite.revoke': 'приглашение отозвано',
  'user.update_quota': 'квота изменена',
  'user.reset_quota': 'квота сброшена',
  'user.reset_password': 'сброс пароля',
  'user.delete': 'юзер удалён',
  'agent.create': 'агент создан',
  'agent.update': 'агент обновлён',
  'agent.delete': 'агент удалён',
  'agent_version.create': 'версия создана',
  'agent_version.set_current': 'версия → current',
  'agent_version.delete': 'версия удалена',
  'tab.create': 'вкладка создана',
  'tab.update': 'вкладка обновлена',
  'tab.delete': 'вкладка удалена',
};

export default async function AdminAuditPage({
  searchParams,
}: {
  searchParams: Promise<{ action?: string; resource_type?: string }>;
}) {
  const sp = await searchParams;
  const params = new URLSearchParams({ limit: '100' });
  if (sp.action) params.set('action', sp.action);
  if (sp.resource_type) params.set('resource_type', sp.resource_type);
  const rows = await apiServer<AuditLogOut[]>(`/api/admin/audit?${params}`);

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-10 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · V.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Журнал<br />
            <span className="italic">действий.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Аудит-трейл: каждое мутирующее admin-действие записано.
            Кто, когда, что сделал, с каким payload.
          </p>
        </div>
        <div className="flex items-end justify-end">
          <div className="text-right">
            <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
              {rows.length}
            </div>
            <div className="ed-eyebrow">записей</div>
          </div>
        </div>
      </div>

      <div className="border-t-2 border-[color:var(--color-text-primary)]">
        <div className="hidden grid-cols-[160px_180px_200px_1fr_140px] items-baseline gap-4 border-b border-[color:var(--color-rule-mute)] py-3 md:grid">
          <span className="ed-eyebrow">Время</span>
          <span className="ed-eyebrow">Действие</span>
          <span className="ed-eyebrow">Ресурс</span>
          <span className="ed-eyebrow">Payload</span>
          <span className="ed-eyebrow">IP</span>
        </div>

        {rows.length === 0 ? (
          <div className="px-4 py-16 text-center">
            <div className="ed-eyebrow mb-2 text-[color:var(--color-text-tertiary)]">
              ПОКА ПУСТО
            </div>
            <p className="font-serif text-base italic text-[color:var(--color-text-secondary)]">
              Записи появятся, как только админ сделает мутирующее действие
              (invite, агент, квота).
            </p>
          </div>
        ) : (
          rows.map((row) => (
            <div
              key={row.id}
              className="grid grid-cols-1 gap-4 border-b border-[color:var(--color-rule-mute)] py-3 md:grid-cols-[160px_180px_200px_1fr_140px] md:items-baseline"
            >
              <span className="font-mono text-xs tabular-nums text-[color:var(--color-text-secondary)]">
                {formatDate(row.created_at)}
              </span>
              <span className="font-serif text-sm">
                {ACTION_LABELS[row.action] ?? row.action}
                <span className="ml-2 font-mono text-xs text-[color:var(--color-text-tertiary)]">
                  {row.action}
                </span>
              </span>
              <span className="font-mono text-xs text-[color:var(--color-text-primary)]">
                {row.resource_type}
                {row.resource_id && (
                  <span className="text-[color:var(--color-text-tertiary)]">
                    {' · '}
                    {row.resource_id.length > 12
                      ? `${row.resource_id.slice(0, 8)}…`
                      : row.resource_id}
                  </span>
                )}
              </span>
              <span className="font-mono text-xs text-[color:var(--color-text-secondary)] break-all">
                {Object.keys(row.payload).length === 0
                  ? '—'
                  : JSON.stringify(row.payload)}
              </span>
              <span className="font-mono text-xs text-[color:var(--color-text-tertiary)]">
                {row.ip ?? '—'}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
