'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';
import { ArrowRight } from 'lucide-react';

interface Props {
  token: string;
  email: string;
}

export function RegisterForm({ token, email }: Props) {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      toast.error('Пароли не совпадают');
      return;
    }
    if (password.length < 12) {
      toast.error('Пароль должен быть от 12 символов');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          token,
          email,
          password,
          display_name: displayName || email.split('@')[0],
        }),
      });
      router.push('/agents' as Route);
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-7">
      <div>
        <label htmlFor="email" className="ed-eyebrow mb-2 block">
          Email (из приглашения)
        </label>
        <input
          id="email"
          type="email"
          value={email}
          readOnly
          disabled
          autoComplete="email"
          className="ed-input cursor-not-allowed font-mono text-[color:var(--color-text-secondary)]"
        />
      </div>

      <div>
        <label htmlFor="display_name" className="ed-eyebrow mb-2 block">
          Имя для портала
        </label>
        <input
          id="display_name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder={email.split('@')[0]}
          disabled={submitting}
          className="ed-input"
        />
        <p className="ed-meta mt-1.5">
          Можно оставить пустым&nbsp;— возьмём из email.
        </p>
      </div>

      <div>
        <label htmlFor="password" className="ed-eyebrow mb-2 block">
          Пароль <span className="text-[color:var(--color-text-tertiary)]">(от&nbsp;12 символов)</span>
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={submitting}
          className="ed-input"
        />
      </div>

      <div>
        <label htmlFor="confirm" className="ed-eyebrow mb-2 block">
          Повторите пароль
        </label>
        <input
          id="confirm"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          autoComplete="new-password"
          disabled={submitting}
          className="ed-input"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="ed-stamp group mt-4 w-full justify-center disabled:opacity-50"
      >
        {submitting ? 'Регистрация…' : (
          <>
            Создать учётную запись
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" strokeWidth={2.5} />
          </>
        )}
      </button>
    </form>
  );
}
