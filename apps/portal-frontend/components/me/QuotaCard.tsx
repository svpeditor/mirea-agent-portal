import type { UserQuotaOut } from '@/lib/api/types';
import { formatDate, formatCurrency } from '@/lib/format';

export function QuotaCard({ quota }: { quota: UserQuotaOut }) {
  const used = parseFloat(quota.period_used_usd) || 0;
  const limit = parseFloat(quota.monthly_limit_usd) || 0;
  const perJob = parseFloat(quota.per_job_cap_usd) || 0;
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const remaining = Math.max(0, limit - used);

  // Color thresholds — academic crimson on warning
  const barColor =
    pct >= 95
      ? 'var(--color-error)'
      : pct >= 75
      ? 'var(--color-gilt)'
      : 'var(--color-forest)';

  return (
    <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr]">
      {/* Main quota display */}
      <div>
        <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
          МЕСЯЧНЫЙ ЛИМИТ LLM
        </div>

        {/* Massive number display */}
        <div className="mb-8 flex items-baseline gap-4">
          <div>
            <div className="font-serif text-7xl font-bold leading-none tabular-nums text-[color:var(--color-text-primary)]">
              {formatCurrency(quota.period_used_usd)}
            </div>
            <div className="mt-2 ed-meta">потрачено за период</div>
          </div>
          <div className="font-serif text-4xl text-[color:var(--color-text-tertiary)]">/</div>
          <div>
            <div className="font-serif text-4xl text-[color:var(--color-text-secondary)]">
              {formatCurrency(quota.monthly_limit_usd)}
            </div>
            <div className="mt-2 ed-meta">месячный лимит</div>
          </div>
        </div>

        {/* Progress with tick marks */}
        <div className="mb-3 flex items-baseline justify-between">
          <span className="ed-eyebrow">ИСПОЛЬЗОВАНИЕ</span>
          <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-primary)]">
            {pct.toFixed(1)}%
          </span>
        </div>
        <div className="relative h-3 w-full overflow-hidden border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)]">
          <div
            className="h-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: barColor }}
          />
          <div className="pointer-events-none absolute inset-0 grid grid-cols-10">
            {Array.from({ length: 9 }).map((_, i) => (
              <span
                key={i}
                className="border-r border-[color:var(--color-bg-primary)] opacity-30"
              />
            ))}
          </div>
        </div>
        <p className="mt-3 ed-meta">
          <span className="text-[color:var(--color-text-tertiary)]">›</span> Период начался{' '}
          <span className="text-[color:var(--color-text-primary)]">{formatDate(quota.period_starts_at)}</span>
          {' '}(МСК). Сбросится 1-го числа следующего месяца.
        </p>
      </div>

      {/* Side stats */}
      <aside className="border-l border-[color:var(--color-rule-mute)] pl-8">
        <div className="space-y-8">
          <div>
            <div className="ed-eyebrow mb-2">ОСТАЛОСЬ В ПЕРИОДЕ</div>
            <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
              {remaining < 0.01 ? '$0.00' : `$${remaining.toFixed(2)}`}
            </div>
          </div>

          <div className="border-t border-[color:var(--color-rule-mute)] pt-6">
            <div className="ed-eyebrow mb-2">ЛИМИТ НА ОДНУ ЗАДАЧУ</div>
            <div className="font-serif text-2xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
              {perJob > 0 ? formatCurrency(quota.per_job_cap_usd) : '—'}
            </div>
            <p className="mt-2 ed-meta">
              На&nbsp;каждом запуске не&nbsp;больше этой суммы.
            </p>
          </div>

          <div className="border-l-2 border-[color:var(--color-accent)] bg-[color:var(--color-bg-tertiary)] p-4">
            <div className="ed-eyebrow mb-2">ПОЯСНЕНИЕ</div>
            <p className="font-serif text-sm leading-relaxed text-[color:var(--color-text-secondary)]">
              Каждый LLM-вызов агента (через&nbsp;OpenRouter) портал считает в&nbsp;USD.
              При исчерпании лимита&nbsp;— новые задачи блокируются до&nbsp;1&nbsp;числа.
              Нужно больше&nbsp;— попросите админа.
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
