import { notFound } from 'next/navigation';
import { apiServer } from '@/lib/api/server';
import { ApiError, type AgentDetailOut } from '@/lib/api/types';
import { AgentForm } from '@/components/agent-form/AgentForm';
import { Badge } from '@/components/ui/badge';

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let agent: AgentDetailOut;
  try {
    agent = await apiServer<AgentDetailOut>(`/api/agents/${slug}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="grid gap-12 lg:grid-cols-[1fr_400px]">
      <div>
        <div className="mb-6 flex items-center gap-3">
          {agent.icon && <span className="text-4xl">{agent.icon}</span>}
          <div>
            <h1 className="font-serif text-4xl">{agent.name}</h1>
            <Badge variant="outline" className="mt-2">
              {agent.manifest.category}
            </Badge>
          </div>
        </div>
        <p className="mb-8 text-lg text-[color:var(--color-text-secondary)]">
          {agent.short_description}
        </p>
      </div>
      <aside>
        <div className="sticky top-8 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-6">
          <h2 className="mb-4 font-serif text-2xl">Запустить</h2>
          <AgentForm manifest={agent.manifest} agentSlug={agent.slug} />
        </div>
      </aside>
    </div>
  );
}
