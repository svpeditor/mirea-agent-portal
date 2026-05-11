'use client';
import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';

interface Cmd {
  id: string;
  label: string;
  group: string;
  href?: Route;
  action?: () => void;
}

interface Props {
  isAdmin: boolean;
}

export function CommandPalette({ isAdmin }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');

  const commands = useMemo<Cmd[]>(() => {
    const base: Cmd[] = [
      { id: 'agents', label: 'Каталог агентов', group: 'НАВИГАЦИЯ', href: '/agents' as Route },
      { id: 'jobs', label: 'Мои запуски', group: 'НАВИГАЦИЯ', href: '/jobs' as Route },
      { id: 'me', label: 'Личный кабинет', group: 'НАВИГАЦИЯ', href: '/me' as Route },
      { id: 'me-quota', label: 'Квота · мой usage', group: 'НАВИГАЦИЯ', href: '/me' as Route },
    ];
    const admin: Cmd[] = isAdmin
      ? [
          { id: 'a-users', label: 'Редакция · юзеры', group: 'АДМИН', href: '/admin/users' as Route },
          { id: 'a-agents', label: 'Редакция · агенты', group: 'АДМИН', href: '/admin/agents' as Route },
          { id: 'a-tabs', label: 'Редакция · вкладки', group: 'АДМИН', href: '/admin/tabs' as Route },
          { id: 'a-usage', label: 'Редакция · LLM usage', group: 'АДМИН', href: '/admin/usage' as Route },
          { id: 'a-audit', label: 'Редакция · аудит-журнал', group: 'АДМИН', href: '/admin/audit' as Route },
          { id: 'a-system', label: 'Редакция · состояние системы', group: 'АДМИН', href: '/admin/system' as Route },
        ]
      : [];
    const utilities: Cmd[] = [
      {
        id: 'logout',
        label: 'Выйти из системы',
        group: 'ДЕЙСТВИЯ',
        action: async () => {
          try {
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
          } catch {
            /* */
          }
          router.push('/login');
          router.refresh();
        },
      },
    ];
    return [...base, ...admin, ...utilities];
  }, [isAdmin, router]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const filtered = useMemo(() => {
    if (!q.trim()) return commands;
    const needle = q.toLowerCase().trim();
    return commands.filter((c) => c.label.toLowerCase().includes(needle));
  }, [q, commands]);

  const grouped = useMemo(() => {
    const map = new Map<string, Cmd[]>();
    for (const c of filtered) {
      const arr = map.get(c.group) ?? [];
      arr.push(c);
      map.set(c.group, arr);
    }
    return Array.from(map.entries());
  }, [filtered]);

  if (!open) return null;

  function execute(c: Cmd) {
    setOpen(false);
    setQ('');
    if (c.href) router.push(c.href);
    else c.action?.();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-8 pt-24"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] shadow-[8px_8px_0_0_var(--color-text-primary)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-[color:var(--color-text-primary)] px-4 py-3">
          <input
            type="text"
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск страниц и действий…"
            className="w-full bg-transparent font-serif text-lg text-[color:var(--color-text-primary)] outline-none placeholder:text-[color:var(--color-text-tertiary)] placeholder:italic"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && filtered[0]) execute(filtered[0]);
            }}
          />
        </div>
        <div className="max-h-[60vh] overflow-y-auto">
          {grouped.length === 0 ? (
            <div className="px-4 py-8 text-center font-serif text-sm italic text-[color:var(--color-text-tertiary)]">
              Ничего не найдено.
            </div>
          ) : (
            grouped.map(([group, items]) => (
              <div key={group} className="py-2">
                <div className="ed-eyebrow px-4 py-1 text-[color:var(--color-text-tertiary)]">
                  {group}
                </div>
                {items.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => execute(c)}
                    className="flex w-full items-center px-4 py-2 text-left font-serif text-sm hover:bg-[color:var(--color-bg-tertiary)] focus:bg-[color:var(--color-bg-tertiary)] focus:outline-none"
                  >
                    <span className="text-[color:var(--color-text-tertiary)]">›</span>
                    <span className="ml-3 flex-1 text-[color:var(--color-text-primary)]">
                      {c.label}
                    </span>
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
        <div className="border-t border-[color:var(--color-rule-mute)] bg-[color:var(--color-bg-tertiary)] px-4 py-2">
          <span className="ed-meta">
            <kbd className="font-mono">⌘K</kbd> · Esc — закрыть
          </span>
        </div>
      </div>
    </div>
  );
}
