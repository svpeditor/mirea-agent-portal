'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';
import { Copy, Check } from 'lucide-react';

interface InviteCreateOut {
  id: string;
  token: string;
  email: string;
  expires_at: string;
  registration_url: string;
}

export function InviteDialog() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [submitting, setSubmitting] = useState(false);
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await apiClient<InviteCreateOut>('/api/admin/invites', {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      });
      // Backend may return absolute or path-only URL. If host present — use as-is, else prefix origin.
      const link = res.registration_url.startsWith('http')
        ? res.registration_url
        : `${window.location.origin}${res.registration_url.startsWith('/') ? '' : '/'}${res.registration_url}`;
      setGeneratedLink(link);
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  function copyLink() {
    if (!generatedLink) return;
    navigator.clipboard.writeText(generatedLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function reset() {
    setOpen(false);
    setEmail('');
    setRole('user');
    setGeneratedLink(null);
  }

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : reset())}>
      <DialogTrigger asChild>
        <Button>Создать инвайт</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новое приглашение</DialogTitle>
        </DialogHeader>

        {!generatedLink ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={submitting}
              />
            </div>
            <div>
              <Label>Роль</Label>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setRole('user')}
                  disabled={submitting}
                  className={`flex-1 border px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] transition-colors ${
                    role === 'user'
                      ? 'border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] text-[color:var(--color-bg-primary)]'
                      : 'border-[color:var(--color-rule-mute)] text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-text-primary)]'
                  }`}
                >
                  Пользователь
                </button>
                <button
                  type="button"
                  onClick={() => setRole('admin')}
                  disabled={submitting}
                  className={`flex-1 border px-3 py-2 font-mono text-xs uppercase tracking-[0.18em] transition-colors ${
                    role === 'admin'
                      ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)] text-[color:var(--color-bg-primary)]'
                      : 'border-[color:var(--color-rule-mute)] text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-accent)]'
                  }`}
                >
                  Админ
                </button>
              </div>
              <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
                Юзер попадёт в каталог агентов. Админ дополнительно получит доступ к разделу /admin.
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Создание...' : 'Создать ссылку'}
            </Button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Скопируй ссылку и отправь её по любому каналу (Telegram, почта).
              Ссылка одноразовая и истекает через 7 дней.
            </p>
            <div className="flex gap-2">
              <Input value={generatedLink} readOnly className="font-mono text-xs" />
              <Button onClick={copyLink} variant={copied ? 'default' : 'outline'} size="icon">
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <Button variant="outline" className="w-full" onClick={reset}>
              Закрыть
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
