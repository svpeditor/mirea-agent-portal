'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { UsagePage } from '@/lib/api/types';
import { formatRelativeTime, formatCurrency } from '@/lib/format';

export function UsageHistoryTable({ page }: { page: UsagePage }) {
  if (page.items.length === 0) {
    return (
      <div className="border border-dashed border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-12 text-center">
        <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
          ХРОНИКА ПУСТА
        </div>
        <h3 className="font-serif text-2xl font-bold">
          Вызовов LLM ещё не&nbsp;было
        </h3>
        <p className="mx-auto mt-3 max-w-md font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
          История появится после запуска агентов с&nbsp;LLM-бэкендом.
          Каждый вызов будет учтён здесь с&nbsp;токенами и&nbsp;стоимостью.
        </p>
      </div>
    );
  }

  // Aggregate stats for header row
  const total = page.items.reduce((s, i) => s + parseFloat(i.cost_usd) || 0, 0);
  const totalTokens = page.items.reduce(
    (s, i) => s + i.prompt_tokens + i.completion_tokens,
    0,
  );

  return (
    <div>
      <div className="mb-6 grid gap-6 md:grid-cols-3">
        <Stat label="Записей" value={page.items.length} mono />
        <Stat label="Токенов всего" value={totalTokens.toLocaleString('ru-RU')} mono />
        <Stat label="Сумма" value={`$${total.toFixed(2)}`} mono accent />
      </div>

      <div className="border-t-2 border-[color:var(--color-text-primary)]">
        {/* Header */}
        <div className="hidden grid-cols-[140px_1fr_1.4fr_120px_120px] items-baseline gap-4 border-b border-[color:var(--color-rule-mute)] py-3 md:grid">
          <span className="ed-eyebrow">Когда</span>
          <span className="ed-eyebrow">Агент</span>
          <span className="ed-eyebrow">Модель</span>
          <span className="ed-eyebrow text-right">Токены</span>
          <span className="ed-eyebrow text-right">Стоимость</span>
        </div>

        {page.items.map((item) => (
          <div
            key={item.id}
            className="grid grid-cols-1 gap-2 border-b border-[color:var(--color-text-primary)] py-3 md:grid-cols-[140px_1fr_1.4fr_120px_120px] md:items-baseline md:gap-4 md:py-3"
          >
            <span className="font-serif text-sm italic text-[color:var(--color-text-secondary)]">
              {formatRelativeTime(item.created_at)}
            </span>
            <Link
              href={`/jobs/${item.job_id}` as Route}
              className="font-mono text-sm text-[color:var(--color-text-primary)] no-underline hover:text-[color:var(--color-accent)]"
            >
              {item.agent_slug ?? '—'}
            </Link>
            <span className="font-mono text-xs text-[color:var(--color-text-secondary)]">
              {item.model}
            </span>
            <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-primary)] md:text-right">
              {(item.prompt_tokens + item.completion_tokens).toLocaleString('ru-RU')}
            </span>
            <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-primary)] md:text-right">
              {formatCurrency(item.cost_usd)}
            </span>
          </div>
        ))}
      </div>

      {page.next_cursor && (
        <div className="mt-6 text-center">
          <Link
            href={`/me?tab=history&cursor=${page.next_cursor}` as Route}
            className="ed-stamp no-underline"
            data-variant="ghost"
          >
            Загрузить ещё
          </Link>
        </div>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
  accent,
}: {
  label: string;
  value: string | number;
  mono?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="border-l-2 border-[color:var(--color-text-primary)] pl-4">
      <div className="ed-eyebrow mb-1">{label}</div>
      <div
        className={`font-serif text-3xl font-bold ${
          mono ? 'tabular-nums' : ''
        } ${accent ? 'text-[color:var(--color-accent)]' : 'text-[color:var(--color-text-primary)]'}`}
      >
        {value}
      </div>
    </div>
  );
}
