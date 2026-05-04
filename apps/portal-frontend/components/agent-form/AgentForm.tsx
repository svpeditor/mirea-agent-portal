'use client';
import type { AgentManifest } from '@/lib/api/types';

interface Props {
  manifest: AgentManifest;
  agentSlug: string;
}

export function AgentForm({ manifest, agentSlug }: Props) {
  return (
    <div className="text-sm text-[color:var(--color-text-secondary)]">
      AgentForm placeholder — детальная имплементация в T13.
      <br />
      Inputs: {Object.keys(manifest.inputs ?? {}).length}
      <br />
      Files: {Object.keys(manifest.files ?? {}).length}
      <br />
      Slug: {agentSlug}
    </div>
  );
}
