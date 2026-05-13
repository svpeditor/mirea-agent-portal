'use client';
import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const LINKS: { href: Route; label: string }[] = [
  { href: '/admin/users' as Route, label: 'Пользователи' },
  { href: '/admin/invites' as Route, label: 'Приглашения' },
  { href: '/admin/agents' as Route, label: 'Агенты' },
  { href: '/admin/tabs' as Route, label: 'Вкладки' },
  { href: '/admin/jobs' as Route, label: 'Запуски' },
  { href: '/admin/crons' as Route, label: 'Расписания' },
  { href: '/admin/usage' as Route, label: 'LLM-usage' },
  { href: '/admin/audit' as Route, label: 'Аудит' },
  { href: '/admin/system' as Route, label: 'Система' },
];

export function AdminSubnav() {
  const pathname = usePathname() || '';
  return (
    <nav className="border-b border-[color:var(--color-rule-mute)] bg-[color:var(--color-bg-secondary)]">
      <div className="mx-auto max-w-[1400px] overflow-x-auto px-8">
        <ul className="flex items-baseline gap-1 whitespace-nowrap py-2">
          {LINKS.map((l) => {
            const active = pathname === l.href || pathname.startsWith(l.href + '/');
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={cn(
                    'px-3 py-1.5 font-mono text-xs uppercase tracking-[0.18em] no-underline transition-colors',
                    active
                      ? 'bg-[color:var(--color-text-primary)] text-[color:var(--color-bg-primary)]'
                      : 'text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-accent)]',
                  )}
                >
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
