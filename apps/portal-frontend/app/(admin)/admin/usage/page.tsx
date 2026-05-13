import { apiServer } from '@/lib/api/server';
import { UsageDashboard } from '@/components/admin/UsageDashboard';

interface AdminUsageSummary {
  total_cost_usd: string;
  total_requests: number;
  by_user: Array<{ user_id: string; email: string; cost_usd: string; requests: number }>;
  by_agent: Array<{ agent_id: string; slug: string; cost_usd: string; requests: number }>;
  by_model: Array<{ model: string; cost_usd: string; requests: number }>;
}

interface AgentBrief {
  id: string;
  slug: string;
  name: string;
}

export default async function AdminUsagePage({
  searchParams,
}: {
  searchParams: Promise<{ agent_id?: string }>;
}) {
  const sp = await searchParams;
  const query = sp.agent_id ? `?agent_id=${encodeURIComponent(sp.agent_id)}` : '';

  const [summary, agents] = await Promise.all([
    apiServer<AdminUsageSummary>(`/api/admin/usage${query}`),
    apiServer<AgentBrief[]>('/api/admin/agents'),
  ]);

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-6 sm:py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · IV.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Бухгалтерия<br />
            <span className="italic">LLM.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Агрегированная статистика расходов LLM по&nbsp;всем подписчикам,
            агентам и&nbsp;моделям. Фильтр&nbsp;— по&nbsp;конкретному агенту.
          </p>
        </div>
      </div>

      <div className="ed-anim-rise ed-d-2">
        <UsageDashboard
          summary={summary}
          agents={agents.map((a) => ({ id: a.id, slug: a.slug, name: a.name }))}
          selectedAgentId={sp.agent_id ?? null}
        />
      </div>
    </div>
  );
}
