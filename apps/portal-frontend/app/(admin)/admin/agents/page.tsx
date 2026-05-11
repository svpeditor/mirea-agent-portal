import { apiServer } from '@/lib/api/server';
import { AgentsTable } from '@/components/admin/AgentsTable';
import { AgentVersionDrawer } from '@/components/admin/AgentVersionDrawer';
import { CreateAgentDialog } from '@/components/admin/CreateAgentDialog';

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
  cost_cap_usd: string | null;
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

  const enabledCount = enrichedAgents.filter((a) => a.enabled).length;

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · II.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Реестр<br />
            <span className="italic">агентов.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Полный реестр агентов: статус сборки, текущая версия, история
            ревизий. Кликайте на&nbsp;строку чтобы&nbsp;открыть карточку.
          </p>
        </div>
        <div className="flex flex-col items-end justify-end gap-6">
          <div className="flex items-end gap-6">
            <div className="text-right">
              <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
                {enrichedAgents.length}
              </div>
              <div className="ed-eyebrow">всего</div>
            </div>
            <div className="text-right">
              <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-accent)]">
                {enabledCount}
              </div>
              <div className="ed-eyebrow">включено</div>
            </div>
          </div>
          <CreateAgentDialog />
        </div>
      </div>

      <div className="ed-anim-rise ed-d-2">
        <AgentsTable agents={enrichedAgents} />
      </div>

      {selected && (
        <AgentVersionDrawer
          agentId={selected.id}
          agentName={selected.name}
          agentSlug={selected.slug}
          gitUrl={selected.git_url}
          enabled={selected.enabled}
          costCapUsd={selected.cost_cap_usd}
        />
      )}
    </div>
  );
}
