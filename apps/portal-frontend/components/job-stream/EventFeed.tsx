'use client';
import type { JobEventOut } from '@/lib/api/types';
import { format } from 'date-fns';
import { CheckCircle2, AlertCircle, Info, Terminal, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

const ICONS: Record<string, LucideIcon> = {
  started: Sparkles,
  item_done: CheckCircle2,
  log: Terminal,
  result: CheckCircle2,
  failed: AlertCircle,
  error: AlertCircle,
  progress: Info,
};

const COLORS: Record<string, string> = {
  started: 'text-[color:var(--color-info)]',
  item_done: 'text-[color:var(--color-success)]',
  log: 'text-[color:var(--color-text-secondary)]',
  result: 'text-[color:var(--color-success)]',
  failed: 'text-[color:var(--color-error)]',
  error: 'text-[color:var(--color-error)]',
  progress: 'text-[color:var(--color-info)]',
};

export function EventFeed({ events }: { events: JobEventOut[] }) {
  const visible = events.filter((e) => e.type !== 'progress');

  if (visible.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-[color:var(--color-text-secondary)]">
        Ожидание событий...
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {visible.map((event) => {
        const Icon = ICONS[event.type] ?? Info;
        const color = COLORS[event.type] ?? '';
        return (
          <li
            key={event.seq}
            className="flex gap-3 border-b border-[color:var(--color-border)] py-2 last:border-b-0"
          >
            <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', color)} />
            <div className="flex-1">
              <div className="text-sm">{formatEventMessage(event)}</div>
              <div className="font-mono text-xs text-[color:var(--color-text-secondary)]">
                {format(new Date(event.ts), 'HH:mm:ss')}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function formatEventMessage(event: JobEventOut): string {
  const p = event.payload as Record<string, unknown>;
  switch (event.type) {
    case 'started':
      return 'Агент запущен';
    case 'item_done':
      return typeof p.summary === 'string' ? `Готово: ${p.summary}` : `Готово (${p.item_id ?? ''})`;
    case 'log':
      return typeof p.message === 'string' ? p.message : JSON.stringify(p);
    case 'result':
      return 'Задача завершена успешно';
    case 'failed':
      return typeof p.message === 'string' ? `Ошибка: ${p.message}` : 'Задача провалилась';
    case 'error':
      return typeof p.message === 'string' ? p.message : 'Произошла ошибка';
    default:
      return event.type;
  }
}
