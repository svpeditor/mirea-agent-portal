import Link from 'next/link';
import type { Route } from 'next';
import type { AgentPublicOut } from '@/lib/api/types';
import { ArrowUpRight } from 'lucide-react';

interface Props {
  agent: AgentPublicOut;
  no: number;
}

// Article entry — one row in the catalog index. Numbered, two-column on hover.
export function AgentCard({ agent, no }: Props) {
  const numStr = String(no).padStart(2, '0');
  return (
    <Link
      href={`/agents/${agent.slug}` as Route}
      className="group block border-b border-[color:var(--color-text-primary)] no-underline transition-colors hover:bg-[color:var(--color-bg-tertiary)]"
    >
      <div className="grid grid-cols-[60px_1fr_auto] items-start gap-4 py-6 pr-4 transition-all group-hover:pl-4 md:gap-8">
        {/* Number column */}
        <div className="pt-1 text-right">
          <div className="font-serif text-2xl font-bold leading-none text-[color:var(--color-text-tertiary)] transition-colors group-hover:text-[color:var(--color-accent)]">
            №&nbsp;{numStr}
          </div>
        </div>

        {/* Main column */}
        <div>
          <div className="ed-eyebrow mb-2 flex items-center gap-2">
            {agent.icon && <span>{agent.icon}</span>}
            <span>{agent.tab.name}</span>
            <span className="text-[color:var(--color-text-tertiary)]">·</span>
            <span className="font-mono">v{agent.current_version.manifest_version}</span>
          </div>
          <h3 className="font-serif text-2xl font-bold leading-tight text-[color:var(--color-text-primary)] transition-colors group-hover:text-[color:var(--color-accent)] md:text-3xl">
            {agent.name}
          </h3>
          <p className="mt-3 max-w-2xl font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
            {agent.short_description}
          </p>
          <div className="mt-3 ed-meta">
            <span className="text-[color:var(--color-text-tertiary)]">slug</span>{' '}
            <code className="text-[color:var(--color-text-primary)]">{agent.slug}</code>
            <span className="mx-3 text-[color:var(--color-text-tertiary)]">·</span>
            <span className="text-[color:var(--color-text-tertiary)]">sha</span>{' '}
            <code className="text-[color:var(--color-text-primary)]">
              {agent.current_version.git_sha.slice(0, 7)}
            </code>
          </div>
        </div>

        {/* Action affordance */}
        <div className="hidden flex-col items-end justify-between self-stretch md:flex">
          <ArrowUpRight
            className="h-6 w-6 text-[color:var(--color-text-tertiary)] transition-all group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:text-[color:var(--color-accent)]"
            strokeWidth={1.5}
          />
          <span className="ed-eyebrow opacity-0 transition-opacity group-hover:opacity-100">
            Открыть&nbsp;→
          </span>
        </div>
      </div>
    </Link>
  );
}
