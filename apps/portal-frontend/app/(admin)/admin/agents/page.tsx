import { apiServer } from '@/lib/api/server';
import { AgentsTable } from '@/components/admin/AgentsTable';
import { AgentVersionDrawer } from '@/components/admin/AgentVersionDrawer';

interface AgentLatestBrief {
  id: string;
  status: string;
  git_sha: string;
  created_at: string;
}

export interface AgentAdminOut {
  id: string;
  slug: string;
  name: string;
  icon: string | null;
  short_description: string;
  tab_id: string;
  current_version_id: string | null;
  enabled: boolean;
  git_url: string;
  created_at: string;
  updated_at: string;
  latest_version: AgentLatestBrief | null;
}

interface TabAdminOut {
  id: string;
  slug: string;
  name: string;
  order_idx: number;
  agents_count: number;
}

export default async function AdminAgentsPage({
  searchParams,
}: {
  searchParams: Promise<{ drawer?: string }>;
}) {
  const { drawer } = await searchParams;
  const [agents, tabs] = await Promise.all([
    apiServer<AgentAdminOut[]>('/api/admin/agents'),
    apiServer<TabAdminOut[]>('/api/admin/tabs'),
  ]);
  const tabById = new Map(tabs.map((t) => [t.id, t.name]));
  const enrichedAgents = agents.map((a) => ({ ...a, tab_name: tabById.get(a.tab_id) ?? '—' }));
  const selected = drawer ? enrichedAgents.find((a) => a.id === drawer) : null;

  return (
    <div>
      <h1 className="mb-6 font-serif text-3xl">Агенты</h1>
      <AgentsTable agents={enrichedAgents} />
      {selected && (
        <AgentVersionDrawer
          agentId={selected.id}
          agentName={selected.name}
          agentSlug={selected.slug}
          gitUrl={selected.git_url}
          enabled={selected.enabled}
        />
      )}
    </div>
  );
}
