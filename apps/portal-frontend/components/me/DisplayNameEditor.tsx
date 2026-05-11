'use client';
import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Pencil, Check, X } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

export function DisplayNameEditor({ current }: { current: string }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(current);
  const [pending, startTransition] = useTransition();
  const [saving, setSaving] = useState(false);

  async function save() {
    const trimmed = val.trim();
    if (!trimmed) {
      toast.error('Имя не может быть пустым');
      return;
    }
    if (trimmed === current) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await apiClient('/api/me', {
        method: 'PATCH',
        body: JSON.stringify({ display_name: trimmed }),
      });
      toast.success('Имя обновлено');
      setEditing(false);
      startTransition(() => router.refresh());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось сохранить');
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <span className="inline-flex items-center gap-2">
        {current}
        <button
          type="button"
          onClick={() => {
            setVal(current);
            setEditing(true);
          }}
          className="text-[color:var(--color-text-tertiary)] hover:text-[color:var(--color-accent)]"
          aria-label="Изменить имя"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2">
      <input
        type="text"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') save();
          if (e.key === 'Escape') setEditing(false);
        }}
        autoFocus
        maxLength={200}
        disabled={saving || pending}
        className="min-w-0 max-w-[18rem] flex-1 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 text-base"
      />
      <button
        type="button"
        onClick={save}
        disabled={saving || pending}
        className="text-[color:var(--color-success)] hover:opacity-80"
        aria-label="Сохранить"
      >
        <Check className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => setEditing(false)}
        disabled={saving || pending}
        className="text-[color:var(--color-text-tertiary)] hover:opacity-80"
        aria-label="Отмена"
      >
        <X className="h-4 w-4" />
      </button>
    </span>
  );
}
