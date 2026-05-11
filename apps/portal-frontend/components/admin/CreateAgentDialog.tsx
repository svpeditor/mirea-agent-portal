'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { ApiError } from '@/lib/api/types';

interface Props {
  /** Не используется напрямую, но дёргаем router.refresh() при success. */
  className?: string;
}

export function CreateAgentDialog({ className }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [gitUrl, setGitUrl] = useState('');
  const [gitRef, setGitRef] = useState('main');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiClient('/api/admin/agents', {
        method: 'POST',
        body: JSON.stringify({ git_url: gitUrl.trim(), git_ref: gitRef.trim() || 'main' }),
      });
      setOpen(false);
      setGitUrl('');
      setGitRef('main');
      router.refresh();
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.body?.error?.message ?? e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ??
          'ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-5 py-2.5 text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)]'
        }
      >
        + Создать агент
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-8 pt-24"
          onClick={() => !submitting && setOpen(false)}
        >
          <div
            className="w-full max-w-lg border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] shadow-[8px_8px_0_0_var(--color-text-primary)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-6 py-3">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-[color:var(--color-bg-primary)]">
                НОВЫЙ АГЕНТ
              </span>
            </div>

            <form onSubmit={onSubmit} className="space-y-5 p-6">
              <p className="ed-meta">
                Платформа клонирует репозиторий, читает manifest.yaml и собирает Docker-образ.
                Манифест должен лежать в корне репо.
              </p>

              <label className="block">
                <span className="ed-eyebrow mb-2 block">Git URL</span>
                <input
                  type="url"
                  required
                  autoFocus
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  placeholder="https://github.com/svpeditor/my-agent.git"
                  className="ed-input w-full"
                />
              </label>

              <label className="block">
                <span className="ed-eyebrow mb-2 block">Git ref</span>
                <input
                  type="text"
                  value={gitRef}
                  onChange={(e) => setGitRef(e.target.value)}
                  placeholder="main"
                  className="ed-input w-full"
                />
                <span className="mt-1 block text-xs italic text-[color:var(--color-text-tertiary)]">
                  Ветка, тэг или commit SHA. По умолчанию main.
                </span>
              </label>

              {error && (
                <div className="border border-[color:var(--color-error)] bg-[color:var(--color-bg-tertiary)] p-3 font-serif text-sm text-[color:var(--color-error)]">
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3 border-t border-[color:var(--color-text-primary)] pt-4">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  disabled={submitting}
                  className="px-4 py-2 font-mono text-xs uppercase tracking-wider hover:text-[color:var(--color-accent)] disabled:opacity-50"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={submitting || !gitUrl.trim()}
                  className="ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-5 py-2 text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)] disabled:opacity-50"
                >
                  {submitting ? 'СОЗДАНИЕ…' : 'СОЗДАТЬ'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
