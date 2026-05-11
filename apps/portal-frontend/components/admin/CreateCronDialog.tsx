'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';

interface AgentBrief {
  id: string;
  slug: string;
  name: string;
}

export function CreateCronDialog({ agents }: { agents: AgentBrief[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [agentId, setAgentId] = useState(agents[0]?.id ?? '');
  const [schedule, setSchedule] = useState<'hourly' | 'daily' | 'weekly' | 'monthly'>('daily');
  const [paramsJson, setParamsJson] = useState('{}');
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    let params: object;
    try {
      params = JSON.parse(paramsJson || '{}');
    } catch {
      toast.error('Невалидный JSON в params');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient('/api/admin/cron_jobs', {
        method: 'POST',
        body: JSON.stringify({ agent_id: agentId, schedule, params }),
      });
      toast.success('Расписание создано');
      setOpen(false);
      setParamsJson('{}');
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Не удалось');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>+ Расписание</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новое расписание</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label htmlFor="agent">Агент</Label>
            <select
              id="agent"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="mt-1 w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-3 py-2"
              required
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.slug})
                </option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="schedule">Частота</Label>
            <select
              id="schedule"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value as typeof schedule)}
              className="mt-1 w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-3 py-2"
            >
              <option value="hourly">Каждый час</option>
              <option value="daily">Ежедневно</option>
              <option value="weekly">Еженедельно</option>
              <option value="monthly">Ежемесячно</option>
            </select>
          </div>

          <div>
            <Label htmlFor="params">Параметры (JSON)</Label>
            <textarea
              id="params"
              value={paramsJson}
              onChange={(e) => setParamsJson(e.target.value)}
              rows={6}
              placeholder='{"topic":"...","max_papers":5}'
              className="mt-1 w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] p-3 font-mono text-sm"
            />
            <p className="ed-meta mt-1 text-[color:var(--color-text-tertiary)]">
              Поля точно как в форме запуска агента вручную.
            </p>
          </div>

          <Button type="submit" disabled={submitting || !agentId}>
            {submitting ? 'Создаю...' : 'Создать расписание'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
