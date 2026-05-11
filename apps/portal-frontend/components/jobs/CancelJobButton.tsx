'use client';
import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { ApiError } from '@/lib/api/types';

interface Props {
  jobId: string;
  /** Текущий статус — кнопка показывается только для queued/running. */
  status: string;
}

const ACTIVE_STATUSES = new Set(['queued', 'running']);

export function CancelJobButton({ jobId, status }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!ACTIVE_STATUSES.has(status)) return null;

  async function doCancel() {
    setError(null);
    try {
      await apiClient(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
      startTransition(() => router.refresh());
      setConfirmOpen(false);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.body?.error?.message ?? `Ошибка: ${e.status}`);
      } else {
        setError(String(e));
      }
    }
  }

  return (
    <div className="mb-6 border-2 border-[color:var(--color-error)] bg-[color:var(--color-bg-tertiary)] p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="ed-eyebrow text-[color:var(--color-error)]">УПРАВЛЕНИЕ ЗАПУСКОМ</div>
          <p className="mt-1 font-serif text-sm text-[color:var(--color-text-secondary)]">
            Job в состоянии <span className="font-mono">{status}</span>. Можно отменить.
          </p>
        </div>
        {!confirmOpen ? (
          <button
            type="button"
            onClick={() => setConfirmOpen(true)}
            className="ed-stamp border-2 border-[color:var(--color-error)] bg-[color:var(--color-bg-primary)] px-4 py-2 text-[color:var(--color-error)] hover:bg-[color:var(--color-error)] hover:text-[color:var(--color-bg-primary)]"
          >
            ОТМЕНИТЬ
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setConfirmOpen(false)}
              disabled={pending}
              className="px-3 py-2 font-mono text-xs uppercase tracking-wider hover:text-[color:var(--color-accent)]"
            >
              Нет
            </button>
            <button
              type="button"
              onClick={doCancel}
              disabled={pending}
              className="ed-stamp border-2 border-[color:var(--color-error)] bg-[color:var(--color-error)] px-4 py-2 text-[color:var(--color-bg-primary)] disabled:opacity-50"
            >
              {pending ? 'ОТМЕНА…' : 'ДА, ОТМЕНИТЬ'}
            </button>
          </div>
        )}
      </div>
      {error && (
        <p className="mt-3 font-serif text-sm text-[color:var(--color-error)]">{error}</p>
      )}
    </div>
  );
}
