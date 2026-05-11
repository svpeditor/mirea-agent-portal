'use client';
import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

interface Props {
  initial: boolean;
}

export function NotifyToggle({ initial }: Props) {
  const router = useRouter();
  const [checked, setChecked] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [pending, startTransition] = useTransition();

  async function toggle(next: boolean) {
    const before = checked;
    setChecked(next);
    setSaving(true);
    try {
      await apiClient('/api/me', {
        method: 'PATCH',
        body: JSON.stringify({ notify_on_job_finish: next }),
      });
      toast.success(next ? 'Уведомления включены' : 'Уведомления выключены');
      startTransition(() => router.refresh());
    } catch (err) {
      setChecked(before);
      toast.error(err instanceof Error ? err.message : 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  }

  const busy = saving || pending;

  return (
    <label className="flex cursor-pointer items-start gap-3 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-4">
      <input
        type="checkbox"
        checked={checked}
        disabled={busy}
        onChange={(e) => toggle(e.target.checked)}
        className="mt-1 h-4 w-4"
      />
      <div className="flex-1">
        <div className="font-serif text-base text-[color:var(--color-text-primary)]">
          Email-уведомления о завершении запуска
        </div>
        <div className="ed-meta text-[color:var(--color-text-tertiary)]">
          Если запуск длится больше 30 секунд, на твой email придёт письмо со ссылкой на результат.
        </div>
      </div>
    </label>
  );
}
