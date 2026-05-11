'use client';
import Link from 'next/link';
import { useSearchParams, usePathname } from 'next/navigation';
import type { Route } from 'next';

const FILTERS: Array<{ id: string; label: string; statuses: string[] | null }> = [
  { id: 'all', label: 'Все', statuses: null },
  { id: 'active', label: 'Активные', statuses: ['queued', 'running'] },
  { id: 'ready', label: 'Готовые', statuses: ['ready'] },
  { id: 'failed', label: 'Ошибки', statuses: ['failed', 'timed_out'] },
  { id: 'cancelled', label: 'Отменённые', statuses: ['cancelled'] },
];

interface Props {
  counts: Record<string, number>;
  /** Текущий выбор. По умолчанию 'all'. */
  active: string;
}

export function JobsFilterBar({ counts, active }: Props) {
  const pathname = usePathname();
  const params = useSearchParams();

  function hrefFor(id: string): Route {
    const next = new URLSearchParams(params);
    if (id === 'all') next.delete('filter');
    else next.set('filter', id);
    const qs = next.toString();
    return `${pathname}${qs ? `?${qs}` : ''}` as Route;
  }

  return (
    <div className="ed-anim-rise mb-6 flex flex-wrap items-center gap-2 border-b border-[color:var(--color-rule-mute)] pb-4">
      {FILTERS.map((f) => {
        const isActive = active === f.id;
        const count = countFor(counts, f);
        return (
          <Link
            key={f.id}
            href={hrefFor(f.id)}
            className={`font-mono text-xs uppercase tracking-wider transition-colors no-underline ${
              isActive
                ? 'border-b-2 border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                : 'text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text-primary)]'
            } px-3 py-2`}
          >
            {f.label}
            <span className="ml-2 tabular-nums text-[color:var(--color-text-tertiary)]">
              {count}
            </span>
          </Link>
        );
      })}
    </div>
  );
}

function countFor(
  counts: Record<string, number>,
  filter: { id: string; statuses: string[] | null },
): number {
  if (filter.statuses === null) {
    return Object.values(counts).reduce((s, n) => s + n, 0);
  }
  return filter.statuses.reduce((s, st) => s + (counts[st] ?? 0), 0);
}
