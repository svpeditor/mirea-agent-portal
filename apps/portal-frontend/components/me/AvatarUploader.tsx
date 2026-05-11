'use client';
import { useRef, useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

const MAX_BYTES = 2 * 1024 * 1024;
const ALLOWED = ['image/png', 'image/jpeg', 'image/webp'];

interface Props {
  hasAvatar: boolean;
  initials: string;
}

export function AvatarUploader({ hasAvatar, initials }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  // cache-buster: уникальный id чтобы заменить картинку после upload/delete
  const [bust, setBust] = useState(0);
  const [pending, startTransition] = useTransition();
  const [uploading, setUploading] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!ALLOWED.includes(f.type)) {
      toast.error('Только PNG, JPEG или WebP');
      return;
    }
    if (f.size > MAX_BYTES) {
      toast.error('Файл больше 2 МБ');
      return;
    }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', f);
      await apiClient('/api/me/avatar', { method: 'POST', body: fd });
      toast.success('Аватар обновлён');
      setBust(Date.now());
      startTransition(() => router.refresh());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось загрузить аватар');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function handleDelete() {
    if (!confirm('Удалить аватар?')) return;
    try {
      await apiClient('/api/me/avatar', { method: 'DELETE' });
      toast.success('Аватар удалён');
      setBust(Date.now());
      startTransition(() => router.refresh());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось удалить');
    }
  }

  const busy = uploading || pending;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-1">
        <div className="relative flex h-32 w-32 items-center justify-center overflow-hidden bg-[color:var(--color-text-primary)] font-serif text-6xl font-bold text-[color:var(--color-bg-primary)]">
          {hasAvatar ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`/api/me/avatar?v=${bust}`}
              alt="Аватар"
              className="h-full w-full object-cover"
            />
          ) : (
            <span>{initials}</span>
          )}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED.join(',')}
        className="hidden"
        onChange={handleFile}
      />
      <div className="flex flex-col items-stretch gap-2 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          <Camera className="mr-2 h-3.5 w-3.5" />
          {hasAvatar ? 'Заменить' : 'Загрузить'}
        </Button>
        {hasAvatar && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={handleDelete}
            className="text-[color:var(--color-error)]"
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" />
            Удалить
          </Button>
        )}
      </div>
      <p className="ed-meta max-w-[14rem] text-center text-[color:var(--color-text-tertiary)]">
        PNG/JPEG/WebP, до 2 МБ
      </p>
    </div>
  );
}
