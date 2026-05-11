'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';

interface Props {
  agentId: string;
  onCreated: () => void;
}

export function CreateAgentVersionForm({ agentId, onCreated }: Props) {
  const [gitRef, setGitRef] = useState('main');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient(`/api/admin/agents/${agentId}/versions`, {
        method: 'POST',
        body: JSON.stringify({ git_ref: gitRef }),
      });
      toast.success('Build запущен');
      onCreated();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-3 space-y-3 rounded-md border border-[color:var(--color-border)] p-3"
    >
      <div>
        <Label htmlFor="git_ref">Git ref (branch / tag / commit)</Label>
        <Input
          id="git_ref"
          value={gitRef}
          onChange={(e) => setGitRef(e.target.value)}
          placeholder="main"
          required
        />
        <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
          Git URL зафиксирован на агенте. Здесь — только новый ref для пересборки.
        </p>
      </div>
      <Button type="submit" disabled={submitting} className="w-full">
        {submitting ? 'Запуск...' : 'Запустить build'}
      </Button>
    </form>
  );
}
