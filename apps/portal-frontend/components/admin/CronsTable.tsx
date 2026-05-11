'use client';
import { useRouter } from 'next/navigation';
import type { ColumnDef } from '@tanstack/react-table';
import { AdminTable } from './AdminTable';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatDate } from '@/lib/format';

interface CronJobAdmin {
  id: string;
  agent_id: string;
  agent_slug: string;
  agent_name: string;
  schedule: 'hourly' | 'daily' | 'weekly' | 'monthly';
  params: Record<string, unknown>;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string;
  last_job_id: string | null;
  created_by_email: string;
}

const SCHEDULE_RU: Record<string, string> = {
  hourly: 'каждый час',
  daily: 'ежедневно',
  weekly: 'еженедельно',
  monthly: 'ежемесячно',
};

export function CronsTable({ crons }: { crons: CronJobAdmin[] }) {
  const router = useRouter();

  async function toggle(id: string, enabled: boolean) {
    try {
      await apiClient(`/api/admin/cron_jobs/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !enabled }),
      });
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Ошибка');
    }
  }

  async function remove(id: string) {
    if (!confirm('Удалить расписание?')) return;
    try {
      await apiClient(`/api/admin/cron_jobs/${id}`, { method: 'DELETE' });
      toast.success('Удалено');
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Ошибка');
    }
  }

  const columns: ColumnDef<CronJobAdmin>[] = [
    {
      accessorKey: 'agent_name',
      header: 'Агент',
      cell: (c) => (
        <div>
          <div className="font-medium">{c.row.original.agent_name}</div>
          <code className="font-mono text-xs text-[color:var(--color-text-secondary)]">
            {c.row.original.agent_slug}
          </code>
        </div>
      ),
    },
    {
      accessorKey: 'schedule',
      header: 'Расписание',
      cell: (c) => (
        <Badge variant="outline">{SCHEDULE_RU[c.row.original.schedule]}</Badge>
      ),
    },
    {
      accessorKey: 'next_run_at',
      header: 'Следующий запуск',
      cell: (c) => (
        <span className="font-mono text-sm tabular-nums">
          {formatDate(c.row.original.next_run_at)}
        </span>
      ),
    },
    {
      accessorKey: 'last_run_at',
      header: 'Последний',
      cell: (c) => (
        <span className="font-mono text-xs text-[color:var(--color-text-secondary)]">
          {c.row.original.last_run_at ? formatDate(c.row.original.last_run_at) : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'enabled',
      header: 'Активно',
      cell: (c) => (
        <Badge variant={c.row.original.enabled ? 'default' : 'outline'}>
          {c.row.original.enabled ? 'on' : 'off'}
        </Badge>
      ),
    },
    {
      id: 'created_by',
      header: 'Кем создано',
      cell: (c) => (
        <code className="font-mono text-xs">{c.row.original.created_by_email}</code>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: (c) => (
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => toggle(c.row.original.id, c.row.original.enabled)}
          >
            {c.row.original.enabled ? 'Выкл' : 'Вкл'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => remove(c.row.original.id)}
            className="text-[color:var(--color-error)]"
          >
            Удалить
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminTable
      data={crons}
      columns={columns}
      emptyTitle="Расписаний пока нет"
      emptyDescription="Создай первое — например, запуск proverka раз в неделю с фиксированной папкой."
    />
  );
}
