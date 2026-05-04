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
    <div>
      <h1 className="mb-6 font-serif text-3xl">Использование LLM</h1>
      <UsageDashboard
        summary={summary}
        agents={agents.map((a) => ({ id: a.id, slug: a.slug, name: a.name }))}
        selectedAgentId={sp.agent_id ?? null}
      />
    </div>
  );
}
