'use client';
import { useRouter, useSearchParams } from 'next/navigation';
import { AdminTable } from './AdminTable';
import { Badge } from '@/components/ui/badge';
import { formatRelativeTime } from '@/lib/format';
import type { ColumnDef } from '@tanstack/react-table';

interface AgentRow {
  id: string;
  slug: string;
  name: string;
  tab_name: string;
  enabled: boolean;
  latest_version: { id: string; status: string; git_sha: string; created_at: string } | null;
}

const COLUMNS: ColumnDef<AgentRow>[] = [
  { accessorKey: 'name', header: 'Имя', cell: (c) => <strong>{c.row.original.name}</strong> },
  {
    accessorKey: 'slug',
    header: 'Slug',
    cell: (c) => <code className="font-mono text-xs">{c.row.original.slug}</code>,
  },
  { accessorKey: 'tab_name', header: 'Таб' },
  {
    accessorKey: 'enabled',
    header: 'Статус',
    cell: (c) => (
      <Badge variant={c.row.original.enabled ? 'default' : 'outline'}>
        {c.row.original.enabled ? 'Включён' : 'Отключён'}
      </Badge>
    ),
  },
  {
    id: 'latest_version',
    header: 'Последняя версия',
    cell: (c) => {
      const lv = c.row.original.latest_version;
      if (!lv) return <span className="text-[color:var(--color-text-secondary)]">—</span>;
      return (
        <div className="text-sm">
          <Badge variant={lv.status === 'ready' ? 'default' : lv.status === 'failed' ? 'destructive' : 'outline'}>
            {lv.status}
          </Badge>{' '}
          <span className="ml-2 font-mono text-xs text-[color:var(--color-text-secondary)]">
            {lv.git_sha.slice(0, 7)}
          </span>
        </div>
      );
    },
  },
  {
    id: 'last_built_at',
    header: 'Build',
    cell: (c) => {
      const lv = c.row.original.latest_version;
      if (!lv) return '—';
      return (
        <span className="text-sm text-[color:var(--color-text-secondary)]">
          {formatRelativeTime(lv.created_at)}
        </span>
      );
    },
  },
];

export function AgentsTable({ agents }: { agents: AgentRow[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  return (
    <AdminTable
      data={agents}
      columns={COLUMNS}
      onRowClick={(a) => {
        const params = new URLSearchParams(searchParams);
        params.set('drawer', a.id);
        router.push(`?${params.toString()}` as never);
      }}
      emptyTitle="Агентов пока нет"
      emptyDescription="Создай первого через POST /api/admin/agents (CLI пока)."
    />
  );
}
