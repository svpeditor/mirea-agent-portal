'use client';
import type { JobEventOut } from '@/lib/api/types';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

// Editorial event feed — like a typewriter print-out / live transcript.
// Numbered lines, monospace timestamp prefix, glyph instead of icon component.

const GLYPHS: Record<string, string> = {
  started: '▸',
  item_done: '✓',
  log: '·',
  result: '◆',
  failed: '✕',
  error: '✕',
  progress: '◐',
};

const COLORS: Record<string, string> = {
  started: 'text-[color:var(--color-info)]',
  item_done: 'text-[color:var(--color-forest)]',
  log: 'text-[color:var(--color-text-tertiary)]',
  result: 'text-[color:var(--color-accent)]',
  failed: 'text-[color:var(--color-error)]',
  error: 'text-[color:var(--color-error)]',
  progress: 'text-[color:var(--color-info)]',
};

export function EventFeed({ events }: { events: JobEventOut[] }) {
  const visible = events.filter((e) => e.type !== 'progress');

  if (visible.length === 0) {
    return (
      <div className="border border-dashed border-[color:var(--color-rule-mute)] bg-[color:var(--color-bg-tertiary)] py-12 text-center">
        <div className="ed-eyebrow mb-2 text-[color:var(--color-text-tertiary)]">
          ОЖИДАНИЕ
        </div>
        <p className="font-serif text-base italic text-[color:var(--color-text-secondary)]">
          Первое событие появится здесь, как только агент начнёт работу.
        </p>
      </div>
    );
  }

  return (
    <ol className="border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)]">
      {visible.map((event, i) => {
        const glyph = GLYPHS[event.type] ?? '·';
        const color = COLORS[event.type] ?? '';
        return (
          <li
            key={event.seq}
            className={cn(
              'group flex gap-4 border-b border-[color:var(--color-rule-mute)] px-4 py-2.5 last:border-b-0',
              'ed-anim-fade hover:bg-[color:var(--color-bg-primary)]',
            )}
            style={{ animationDelay: `${Math.min(i * 0.04, 0.4)}s` }}
          >
            {/* Sequence number */}
            <span className="w-10 shrink-0 font-mono text-xs tabular-nums text-[color:var(--color-text-tertiary)]">
              {String(event.seq).padStart(3, '0')}
            </span>

            {/* Glyph */}
            <span className={cn('w-3 shrink-0 font-mono text-base leading-none', color)}>
              {glyph}
            </span>

            {/* Time */}
            <span className="w-20 shrink-0 font-mono text-xs tabular-nums text-[color:var(--color-text-secondary)]">
              {format(new Date(event.ts), 'HH:mm:ss')}
            </span>

            {/* Message */}
            <span className="flex-1 font-mono text-sm text-[color:var(--color-text-primary)]">
              {formatEventMessage(event)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function formatEventMessage(event: JobEventOut): string {
  const p = event.payload as Record<string, unknown>;
  // SDK-контракт (portal_sdk/events.py): log/error/failed используют `msg`,
  // item_done — `id` + `summary`. Раньше тут читались несуществующие поля,
  // и весь поток событий рендерился пустыми строками.
  switch (event.type) {
    case 'started':
      return 'агент запущен';
    case 'item_done':
      return typeof p.summary === 'string' && p.summary
        ? `готово · ${p.summary}`
        : `готово · ${p.id ?? ''}`;
    case 'log':
      return typeof p.msg === 'string' ? p.msg : JSON.stringify(p);
    case 'result':
      return 'задача завершена успешно';
    case 'failed':
      return typeof p.msg === 'string' ? `сбой · ${p.msg}` : 'задача провалилась';
    case 'error':
      return typeof p.msg === 'string' ? p.msg : 'произошла ошибка';
    default:
      return event.type;
  }
}
