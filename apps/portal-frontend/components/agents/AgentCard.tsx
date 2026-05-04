import Link from 'next/link';
import type { Route } from 'next';
import type { AgentPublicOut } from '@/lib/api/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function AgentCard({ agent }: { agent: AgentPublicOut }) {
  return (
    <Link href={`/agents/${agent.slug}` as Route} className="group no-underline">
      <Card className="h-full transition-colors hover:border-[color:var(--color-accent)]">
        <CardHeader>
          {agent.icon && <div className="text-4xl">{agent.icon}</div>}
          <CardTitle className="text-xl group-hover:text-[color:var(--color-accent)]">
            {agent.name}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CardDescription className="line-clamp-3">{agent.short_description}</CardDescription>
        </CardContent>
      </Card>
    </Link>
  );
}
