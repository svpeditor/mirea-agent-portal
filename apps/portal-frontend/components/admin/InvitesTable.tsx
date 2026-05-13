'use client';
import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import type { ColumnDef } from '@tanstack/react-table';
import { AdminTable } from './AdminTable';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { formatDate } from '@/lib/format';
import { toast } from 'sonner';
import { Copy, Check, X } from 'lucide-react';

export interface InviteRow {
  id: string;
  token: string;
  email: string;
  role: 'user' | 'admin';
  created_by_user_id: string;
  expires_at: string;
  used_at: string | null;
  used_by_user_id: string | null;
  created_at: string;
  registration_url: string | null;
}

type InviteStatus = 'active' | 'used' | 'expired';

function inviteStatus(inv: InviteRow): InviteStatus {
  if (inv.used_at) return 'used';
  if (new Date(inv.expires_at).getTime() < Date.now()) return 'expired';
  return 'active';
}

const STATUS_LABEL: Record<InviteStatus, string> = {
  active: 'активно',
  used: 'использовано',
  expired: 'просрочено',
};

export function InvitesTable({ invites }: { invites: InviteRow[] }) {
  const router = useRouter();
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function copyLink(inv: InviteRow) {
    if (!inv.registration_url) return;
    const link = inv.registration_url.startsWith('http')
      ? inv.registration_url
      : `${window.location.origin}${inv.registration_url.startsWith('/') ? '' : '/'}${inv.registration_url}`;
    await navigator.clipboard.writeText(link);
    setCopiedId(inv.id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  async function cancelInvite(inv: InviteRow) {
    if (!confirm(`Отменить приглашение для ${inv.email}?`)) return;
    try {
      await apiClient(`/api/admin/invites/${inv.id}`, { method: 'DELETE' });
      toast.success('Приглашение отменено');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  const columns: ColumnDef<InviteRow>[] = useMemo(
    () => [
      {
        accessorKey: 'email',
        header: 'Email',
        cell: (ctx) => <span className="font-medium">{ctx.row.original.email}</span>,
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
        id: 'status',
        header: 'Статус',
        cell: (ctx) => {
          const s = inviteStatus(ctx.row.original);
          return (
            <Badge variant={s === 'active' ? 'default' : 'outline'}>
              {STATUS_LABEL[s]}
            </Badge>
          );
        },
      },
      {
        accessorKey: 'created_at',
        header: 'Создано',
        cell: (ctx) => (
          <span className="text-[color:var(--color-text-secondary)]">
            {formatDate(ctx.row.original.created_at)}
          </span>
        ),
      },
      {
        accessorKey: 'expires_at',
        header: 'Истекает',
        cell: (ctx) => (
          <span className="text-[color:var(--color-text-secondary)]">
            {formatDate(ctx.row.original.expires_at)}
          </span>
        ),
      },
      {
        id: 'actions',
        header: '',
        cell: (ctx) => {
          const inv = ctx.row.original;
          const s = inviteStatus(inv);
          if (s !== 'active') return null;
          const copied = copiedId === inv.id;
          return (
            <div className="flex items-center justify-end gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  copyLink(inv);
                }}
                disabled={!inv.registration_url}
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                <span className="ml-1">{copied ? 'Скопировано' : 'Копировать ссылку'}</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  cancelInvite(inv);
                }}
              >
                <X className="h-3 w-3" />
                <span className="ml-1">Отменить</span>
              </Button>
            </div>
          );
        },
      },
    ],
    [copiedId],
  );

  return (
    <AdminTable
      data={invites}
      columns={columns}
      emptyTitle="Нет приглашений"
      emptyDescription="Создайте первое приглашение через диалог в правом верхнем углу."
    />
  );
}
