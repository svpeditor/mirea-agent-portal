'use client';
import { useRouter, useSearchParams } from 'next/navigation';
import type { UserOut } from '@/lib/api/types';
import { AdminTable } from './AdminTable';
import { Badge } from '@/components/ui/badge';
import type { ColumnDef } from '@tanstack/react-table';
import { formatDate } from '@/lib/format';

const COLUMNS: ColumnDef<UserOut>[] = [
  {
    accessorKey: 'email',
    header: 'Email',
    cell: (ctx) => <span className="font-medium">{ctx.row.original.email}</span>,
  },
  {
    accessorKey: 'display_name',
    header: 'Имя',
  },
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
    accessorKey: 'created_at',
    header: 'Создан',
    cell: (ctx) => (
      <span className="text-sm text-[color:var(--color-text-secondary)]">
        {formatDate(ctx.row.original.created_at)}
      </span>
    ),
  },
];

export function UsersTable({ users }: { users: UserOut[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  return (
    <AdminTable
      data={users}
      columns={COLUMNS}
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
