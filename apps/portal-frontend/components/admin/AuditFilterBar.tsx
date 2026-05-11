'use client';
import Link from 'next/link';
import { useSearchParams, usePathname } from 'next/navigation';
import type { Route } from 'next';

const RESOURCE_FILTERS: Array<{ id: string; label: string }> = [
  { id: '', label: 'Все' },
  { id: 'invite', label: 'Приглашения' },
  { id: 'user', label: 'Юзеры' },
  { id: 'user_quota', label: 'Квоты' },
  { id: 'agent', label: 'Агенты' },
  { id: 'agent_version', label: 'Версии' },
  { id: 'tab', label: 'Вкладки' },
];

interface Props {
  active: string;
}

export function AuditFilterBar({ active }: Props) {
  const pathname = usePathname();
  const params = useSearchParams();

  function hrefFor(id: string): Route {
    const next = new URLSearchParams(params);
    if (id === '') next.delete('resource_type');
    else next.set('resource_type', id);
    const qs = next.toString();
    return `${pathname}${qs ? `?${qs}` : ''}` as Route;
  }

  return (
    <div className="ed-anim-rise mb-6 flex flex-wrap items-center gap-2 border-b border-[color:var(--color-rule-mute)] pb-4">
      <span className="ed-eyebrow mr-2 text-[color:var(--color-text-tertiary)]">
        ТИП РЕСУРСА:
      </span>
      {RESOURCE_FILTERS.map((f) => {
        const isActive = active === f.id;
        return (
          <Link
            key={f.id || 'all'}
            href={hrefFor(f.id)}
            className={`font-mono text-xs uppercase tracking-wider transition-colors no-underline ${
              isActive
                ? 'border-b-2 border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                : 'text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text-primary)]'
            } px-3 py-2`}
          >
            {f.label}
          </Link>
        );
      })}
    </div>
  );
}
