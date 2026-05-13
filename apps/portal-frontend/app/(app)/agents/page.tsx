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

  const selectedTab = selectedTabSlug
    ? tabs.find((t) => t.slug === selectedTabSlug)
    : null;

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-6 sm:py-12">
      {/* Page header */}
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РАЗДЕЛ I
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Каталог<br />
            <span className="italic">агентов.</span>
          </h1>
        </div>
        <div className="border-l border-[color:var(--color-rule-mute)] pl-8">
          <p className="font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
            {selectedTab ? (
              <>
                Раздел&nbsp;«<strong className="text-[color:var(--color-text-primary)]">{selectedTab.name}</strong>».
                Показано {filteredAgents.length} из&nbsp;{agents.length} агентов.
              </>
            ) : (
              <>
                Полный реестр готовых к&nbsp;запуску AI-агентов.
                Всего опубликовано <strong className="text-[color:var(--color-text-primary)]">{agents.length}</strong> агентов
                в&nbsp;{tabs.length} разделах.
              </>
            )}
          </p>
          <p className="mt-3 ed-meta">
            Обновлено {new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long' }).format(new Date())}
          </p>
        </div>
      </div>

      {/* Layout: sidebar + index */}
      <div className="grid gap-12 md:grid-cols-[260px_1fr]">
        <TabsSidebar tabs={tabs} selectedSlug={selectedTabSlug ?? null} />
        <div>
          {filteredAgents.length === 0 ? (
            <EmptyState
              title="В этом разделе пока пусто"
              description="Попросите админа НУГ опубликовать подходящего агента или зайдите в другой раздел."
            />
          ) : (
            <div className="border-t-2 border-[color:var(--color-text-primary)]">
              {filteredAgents.map((agent, i) => (
                <AgentCard key={agent.id} agent={agent} no={i + 1} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
