import { apiServer } from '@/lib/api/server';
import type { TabOut, AgentPublicOut } from '@/lib/api/types';
import { TabsSidebar } from '@/components/agents/TabsSidebar';
import { AgentCard } from '@/components/agents/AgentCard';
import { EmptyState } from '@/components/empty-state';

export default async function AgentsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const { tab: selectedTabSlug } = await searchParams;

  const [tabs, agents] = await Promise.all([
    apiServer<TabOut[]>('/api/tabs'),
    apiServer<AgentPublicOut[]>('/api/agents'),
  ]);

  const filteredAgents = selectedTabSlug
    ? agents.filter((a) => a.tab.slug === selectedTabSlug)
    : agents;

  return (
    <div className="grid gap-8 md:grid-cols-[200px_1fr]">
      <TabsSidebar tabs={tabs} selectedSlug={selectedTabSlug ?? null} />
      <div>
        {filteredAgents.length === 0 ? (
          <EmptyState
            title="Здесь пока нет агентов"
            description="Спроси админа НУГ — он опубликует подходящего."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
