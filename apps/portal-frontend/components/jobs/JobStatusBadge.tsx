import type { JobStatus } from '@/lib/api/types';
import { cn } from '@/lib/utils';

// Editorial status badges — small caps mono labels, like a journal categorization stamp.
// Each status has its own glyph for visual distinctiveness.

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'В ОЧЕРЕДИ',
  running: 'ВЫПОЛНЯЕТСЯ',
  ready: 'ГОТОВО',
  succeeded: 'ГОТОВО',
  failed: 'ОШИБКА',
  cancelled: 'ОТМЕНЕНО',
  timed_out: 'ТАЙМ-АУТ',
};

const STATUS_GLYPH: Record<JobStatus, string> = {
  queued: '○',
  running: '◐',
  ready: '●',
  succeeded: '●',
  failed: '✕',
  cancelled: '⊘',
  timed_out: '⏱',
};

const STATUS_STYLES: Record<JobStatus, string> = {
  queued:
    'border-[color:var(--color-text-tertiary)] text-[color:var(--color-text-tertiary)]',
  running:
    'border-[color:var(--color-info)] bg-[color:var(--color-info)] text-[color:var(--color-bg-primary)] [animation:ed-fade-in_2s_ease-in-out_infinite_alternate]',
  ready:
    'border-[color:var(--color-forest)] bg-[color:var(--color-forest)] text-[color:var(--color-bg-primary)]',
  succeeded:
    'border-[color:var(--color-forest)] bg-[color:var(--color-forest)] text-[color:var(--color-bg-primary)]',
  failed:
    'border-[color:var(--color-error)] bg-[color:var(--color-error)] text-[color:var(--color-bg-primary)]',
  cancelled:
    'border-[color:var(--color-text-secondary)] text-[color:var(--color-text-secondary)]',
  timed_out:
    'border-[color:var(--color-gilt)] bg-[color:var(--color-gilt)] text-[color:var(--color-bg-primary)]',
};

export function JobStatusBadge({
  status,
  size = 'default',
}: {
  status: JobStatus;
  size?: 'sm' | 'default' | 'lg';
}) {
  const sizeClass =
    size === 'sm'
      ? 'text-[0.6rem] px-1.5 py-0.5 tracking-[0.15em]'
      : size === 'lg'
      ? 'text-xs px-3 py-1.5 tracking-[0.2em]'
      : 'text-[0.65rem] px-2 py-1 tracking-[0.18em]';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 border font-mono uppercase whitespace-nowrap',
        STATUS_STYLES[status],
        sizeClass,
      )}
    >
      <span className="text-current">{STATUS_GLYPH[status]}</span>
      {STATUS_LABELS[status]}
    </span>
  );
}
