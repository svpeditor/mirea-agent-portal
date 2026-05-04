'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { DrawerSheet } from './DrawerSheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';
import { formatCurrency, formatDate } from '@/lib/format';
import type { UserOut } from '@/lib/api/types';

interface UserAdminOut extends UserOut {
  quota: {
    monthly_limit_usd: string;
    period_used_usd: string;
    per_job_cap_usd: string;
    period_starts_at: string;
  } | null;
}

interface Props {
  user: UserAdminOut | null;
}

export function UserDrawer({ user }: Props) {
  const router = useRouter();
  const [monthlyLimit, setMonthlyLimit] = useState(user?.quota?.monthly_limit_usd ?? '');
  const [perJobCap, setPerJobCap] = useState(user?.quota?.per_job_cap_usd ?? '');
  const [saving, setSaving] = useState(false);

  if (!user) return null;

  async function saveQuota() {
    if (!user) return;
    setSaving(true);
    try {
      await apiClient(`/api/admin/users/${user.id}/quota`, {
        method: 'PATCH',
        body: JSON.stringify({
          monthly_limit_usd: monthlyLimit,
          per_job_cap_usd: perJobCap,
        }),
      });
      toast.success('Квота обновлена');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function resetQuota() {
    if (!user) return;
    setSaving(true);
    try {
      await apiClient(`/api/admin/users/${user.id}/quota/reset`, { method: 'POST' });
      toast.success('Квота сброшена');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function resetPassword() {
    if (!user) return;
    setSaving(true);
    try {
      const res = await apiClient<{ temporary_password: string }>(
        `/api/admin/users/${user.id}/reset-password`,
        { method: 'POST' },
      );
      toast.success(`Временный пароль: ${res.temporary_password}`, { duration: 30000 });
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <DrawerSheet paramName="drawer" paramValue={user.id} title={user.email}>
      <div className="space-y-6">
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-[color:var(--color-text-secondary)]">Имя:</span> {user.display_name}
          </div>
          <div>
            <span className="text-[color:var(--color-text-secondary)]">Роль:</span>{' '}
            <code className="font-mono">{user.role}</code>
          </div>
          <div>
            <span className="text-[color:var(--color-text-secondary)]">Создан:</span> {formatDate(user.created_at)}
          </div>
        </div>

        {user.quota ? (
          <div className="space-y-3 rounded-md border border-[color:var(--color-border)] p-4">
            <h3 className="font-serif text-lg">Квота</h3>
            <div className="text-sm">
              Использовано: <span className="font-mono">{formatCurrency(user.quota.period_used_usd)}</span> /{' '}
              <span className="font-mono">{formatCurrency(user.quota.monthly_limit_usd)}</span>
            </div>
            <div>
              <Label htmlFor="monthly_limit">Месячный лимит, USD</Label>
              <Input
                id="monthly_limit"
                type="text"
                value={monthlyLimit}
                onChange={(e) => setMonthlyLimit(e.target.value)}
                placeholder="5.0000"
              />
            </div>
            <div>
              <Label htmlFor="per_job_cap">Лимит на задачу, USD</Label>
              <Input
                id="per_job_cap"
                type="text"
                value={perJobCap}
                onChange={(e) => setPerJobCap(e.target.value)}
                placeholder="0.5000"
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={saveQuota} disabled={saving}>
                Сохранить
              </Button>
              <Button variant="outline" onClick={resetQuota} disabled={saving}>
                Сбросить period_used
              </Button>
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-[color:var(--color-border)] p-4 text-sm text-[color:var(--color-text-secondary)]">
            Квота не назначена. Будет создана автоматически при первой LLM-задаче.
          </div>
        )}

        <div className="rounded-md border border-[color:var(--color-border)] p-4">
          <h3 className="font-serif text-lg">Пароль</h3>
          <p className="my-2 text-sm text-[color:var(--color-text-secondary)]">
            Сгенерировать временный пароль, чтобы юзер смог войти и сменить.
          </p>
          <Button variant="outline" onClick={resetPassword} disabled={saving}>
            Сбросить пароль
          </Button>
        </div>
      </div>
    </DrawerSheet>
  );
}
