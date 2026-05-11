import { apiServer } from '@/lib/api/server';
import { CronsTable } from '@/components/admin/CronsTable';
import { CreateCronDialog } from '@/components/admin/CreateCronDialog';

interface AgentBrief {
  id: string;
  slug: string;
  name: string;
  current_version_id: string | null;
}

interface CronJobAdmin {
  id: string;
  agent_id: string;
  agent_slug: string;
  agent_name: string;
  schedule: 'hourly' | 'daily' | 'weekly' | 'monthly';
  params: Record<string, unknown>;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string;
  last_job_id: string | null;
  created_by_email: string;
  created_at: string;
}

export default async function AdminCronsPage() {
  const [crons, agents] = await Promise.all([
    apiServer<CronJobAdmin[]>('/api/admin/cron_jobs'),
    apiServer<AgentBrief[]>('/api/admin/agents'),
  ]);

  const activeAgents = agents.filter((a) => a.current_version_id);

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-8 flex items-end justify-between">
        <div>
          <div className="ed-eyebrow mb-2 text-[color:var(--color-accent)]">III. РЕДАКЦИЯ</div>
          <h1 className="ed-display text-5xl md:text-6xl">Расписание</h1>
          <p className="ed-meta mt-3 max-w-2xl">
            Автоматические запуски агентов по расписанию. Scheduler проверяет
            очередь каждые 60 секунд, кладёт в обычную очередь job&apos;ов.
          </p>
        </div>
        <CreateCronDialog agents={activeAgents} />
      </div>
      <div className="ed-anim-rise ed-d-2">
        <CronsTable crons={crons} />
      </div>
    </div>
  );
}
