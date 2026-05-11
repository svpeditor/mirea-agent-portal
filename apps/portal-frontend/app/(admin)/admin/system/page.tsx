import { apiServer } from '@/lib/api/server';
import { ApiError } from '@/lib/api/types';

interface HealthFull {
  status: 'ok' | 'degraded';
  checks: { postgres: string; redis: string };
  uptime_seconds: number;
  environment: string;
}

async function fetchHealth(): Promise<HealthFull | { error: string }> {
  try {
    return await apiServer<HealthFull>('/api/health/full');
  } catch (err) {
    if (err instanceof ApiError && err.status === 503) {
      // 503 — degraded, бэк всё равно вернул JSON; парсим через detail
      const body = err.body as { detail?: HealthFull } | null;
      if (body?.detail) return body.detail;
    }
    return { error: String(err) };
  }
}

function fmtUptime(seconds: number): string {
  const s = Math.floor(seconds);
  if (s < 60) return `${s}с`;
  if (s < 3600) return `${Math.floor(s / 60)}м ${s % 60}с`;
  if (s < 86400) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}ч ${m}м`;
  }
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  return `${d}д ${h}ч`;
}

export default async function AdminSystemPage() {
  const data = await fetchHealth();
  const isError = 'error' in data;
  const isOk = !isError && data.status === 'ok';

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-10">
        <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
          РЕДАКЦИЯ · VI.
        </div>
        <h1 className="ed-display text-6xl md:text-7xl">
          Состояние<br />
          <span className="italic">системы.</span>
        </h1>
      </div>

      <div className="ed-anim-rise ed-d-2 grid gap-6 md:grid-cols-2">
        <div className="border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] p-6">
          <div className="ed-eyebrow mb-3 text-[color:var(--color-text-tertiary)]">
            ОБЩИЙ СТАТУС
          </div>
          <div className="flex items-baseline gap-4">
            <span
              className={`inline-block h-4 w-4 ${
                isError
                  ? 'bg-[color:var(--color-error)]'
                  : isOk
                  ? 'bg-[color:var(--color-forest)]'
                  : 'bg-[color:var(--color-accent)]'
              }`}
            />
            <span className="font-serif text-3xl font-bold">
              {isError ? 'НЕДОСТУПЕН' : isOk ? 'РАБОТАЕТ' : 'ЧАСТИЧНО'}
            </span>
          </div>
          {!isError && (
            <p className="mt-4 font-mono text-xs text-[color:var(--color-text-secondary)]">
              env: <span className="text-[color:var(--color-text-primary)]">{data.environment}</span>
              {' · '}uptime: <span className="text-[color:var(--color-text-primary)]">{fmtUptime(data.uptime_seconds)}</span>
            </p>
          )}
        </div>

        <div className="border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] p-6">
          <div className="ed-eyebrow mb-3 text-[color:var(--color-text-tertiary)]">
            ЗАВИСИМОСТИ
          </div>
          {isError ? (
            <p className="font-mono text-xs text-[color:var(--color-error)] break-all">
              {data.error}
            </p>
          ) : (
            <dl className="space-y-2">
              <CheckRow name="Postgres" status={data.checks.postgres} />
              <CheckRow name="Redis" status={data.checks.redis} />
            </dl>
          )}
        </div>
      </div>

      <div className="ed-anim-rise ed-d-3 mt-12 border-t border-[color:var(--color-text-primary)] pt-6">
        <p className="ed-meta">
          Данные с <code className="font-mono">/api/health/full</code>. Страница не
          обновляется автоматически — перезагрузи для свежих значений.
        </p>
      </div>
    </div>
  );
}

function CheckRow({ name, status }: { name: string; status: string }) {
  const ok = status === 'ok';
  return (
    <div className="flex items-baseline justify-between border-b border-[color:var(--color-rule-mute)] pb-2 last:border-b-0">
      <dt className="font-serif text-base">{name}</dt>
      <dd
        className={`font-mono text-xs ${
          ok ? 'text-[color:var(--color-forest)]' : 'text-[color:var(--color-error)]'
        }`}
      >
        {ok ? '◆ ok' : `✕ ${status}`}
      </dd>
    </div>
  );
}
