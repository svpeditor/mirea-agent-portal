'use client';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMemo } from 'react';
import type { UserOut } from '@/lib/api/types';
import { AdminTable } from './AdminTable';
import { Badge } from '@/components/ui/badge';
import type { ColumnDef } from '@tanstack/react-table';
import { formatDate, formatCurrency } from '@/lib/format';

interface UserRow extends UserOut {
  /** Из агрегата /api/admin/usage; '0' если нет usage логов. */
  llm_cost_usd?: string;
  llm_requests?: number;
}

export function UsersTable({
  users,
  costByUserId = {},
  requestsByUserId = {},
}: {
  users: UserOut[];
  costByUserId?: Record<string, string>;
  requestsByUserId?: Record<string, number>;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const enriched: UserRow[] = useMemo(
    () =>
      users.map((u) => ({
        ...u,
        llm_cost_usd: costByUserId[u.id] ?? '0',
        llm_requests: requestsByUserId[u.id] ?? 0,
      })),
    [users, costByUserId, requestsByUserId],
  );

  const columns: ColumnDef<UserRow>[] = useMemo(
    () => [
      {
        accessorKey: 'email',
        header: 'Email',
        cell: (ctx) => <span className="font-medium">{ctx.row.original.email}</span>,
      },
      { accessorKey: 'display_name', header: 'Имя' },
      {
        accessorKey: 'role',
        header: 'Роль',
        cell: (ctx) => (
          <Badge variant={ctx.row.original.role === 'admin' ? 'default' : 'outline'}>
            {ctx.row.original.role}
          </Badge>
        ),
      },
      {
        accessorKey: 'monthly_budget_usd',
        header: 'Лимит',
        cell: (ctx) => (
          <span className="font-mono text-sm tabular-nums">
            ${ctx.row.original.monthly_budget_usd ?? '—'}
          </span>
        ),
      },
      {
        accessorKey: 'llm_cost_usd',
        header: 'LLM, $',
        cell: (ctx) => (
          <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-secondary)]">
            {formatCurrency(ctx.row.original.llm_cost_usd ?? '0')}
          </span>
        ),
      },
      {
        accessorKey: 'llm_requests',
        header: 'Запросов',
        cell: (ctx) => (
          <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-secondary)]">
            {ctx.row.original.llm_requests ?? 0}
          </span>
        ),
      },
      {
        accessorKey: 'created_at',
        header: 'Создан',
        cell: (ctx) => (
          <span className="text-sm text-[color:var(--color-text-secondary)]">
            {formatDate(ctx.row.original.created_at)}
          </span>
        ),
      },
    ],
    [],
  );

  return (
    <AdminTable
      data={enriched}
      columns={columns}
      onRowClick={(u) => {
        const params = new URLSearchParams(searchParams);
        params.set('drawer', u.id);
        router.push(`?${params.toString()}` as never);
      }}
      emptyTitle="Пользователей пока нет"
      emptyDescription="Создай первого через «Создать инвайт»."
    />
  );
}
