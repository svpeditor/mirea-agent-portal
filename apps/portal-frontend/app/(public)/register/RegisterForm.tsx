'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';

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
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="email">Email (из приглашения)</Label>
        <Input
          id="email"
          type="email"
          value={email}
          readOnly
          disabled
          autoComplete="email"
        />
      </div>
      <div>
        <Label htmlFor="display_name">Имя для портала</Label>
        <Input
          id="display_name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder={email.split('@')[0]}
          disabled={submitting}
        />
        <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
          Можно оставить пустым - возьмём из email.
        </p>
      </div>
      <div>
        <Label htmlFor="password">Пароль (от 12 символов)</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          disabled={submitting}
        />
      </div>
      <div>
        <Label htmlFor="confirm">Повтори пароль</Label>
        <Input
          id="confirm"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          autoComplete="new-password"
          disabled={submitting}
        />
      </div>
      <Button type="submit" className="w-full" disabled={submitting}>
        {submitting ? 'Регистрация...' : 'Создать аккаунт'}
      </Button>
    </form>
  );
}
