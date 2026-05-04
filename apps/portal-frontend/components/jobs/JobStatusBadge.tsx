import { Badge } from '@/components/ui/badge';
import type { JobStatus } from '@/lib/api/types';
import { cn } from '@/lib/utils';

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: 'В очереди',
  running: 'Выполняется',
  ready: 'Готово',
  succeeded: 'Готово',
  failed: 'Ошибка',
  cancelled: 'Отменено',
  timed_out: 'Таймаут',
};

const STATUS_STYLES: Record<JobStatus, string> = {
  queued: 'bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-secondary)]',
  running: 'bg-[color:var(--color-info)] text-[color:var(--color-bg-primary)]',
  ready: 'bg-[color:var(--color-success)] text-[color:var(--color-bg-primary)]',
  succeeded: 'bg-[color:var(--color-success)] text-[color:var(--color-bg-primary)]',
  failed: 'bg-[color:var(--color-error)] text-[color:var(--color-bg-primary)]',
  cancelled: 'bg-[color:var(--color-text-secondary)] text-[color:var(--color-bg-primary)]',
  timed_out: 'bg-[color:var(--color-warning)] text-[color:var(--color-bg-primary)]',
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <Badge className={cn(STATUS_STYLES[status])}>{STATUS_LABELS[status]}</Badge>;
}
