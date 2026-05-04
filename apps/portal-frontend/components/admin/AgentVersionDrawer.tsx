'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { DrawerSheet } from './DrawerSheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CreateAgentVersionForm } from './CreateAgentVersionForm';
import { apiClient } from '@/lib/api/client';
import { formatDate } from '@/lib/format';
import { toast } from 'sonner';
import { mapApiError } from '@/lib/api/errors';

interface AgentVersion {
  id: string;
  git_ref: string;
  git_sha: string;
  manifest_version: string;
  status: 'queued' | 'building' | 'ready' | 'failed';
  build_started_at: string | null;
  build_finished_at: string | null;
  build_error: string | null;
  is_current: boolean;
}

interface Props {
  agentId: string;
  agentName: string;
  agentSlug: string;
  gitUrl: string;
  enabled: boolean;
}

export function AgentVersionDrawer({ agentId, agentName, agentSlug, gitUrl, enabled }: Props) {
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);

  const { data: versions, refetch } = useQuery({
    queryKey: ['agent-versions', agentId],
    queryFn: () => apiClient<AgentVersion[]>(`/api/admin/agents/${agentId}/versions`),
    refetchInterval: (query) => {
      const data = query.state.data as AgentVersion[] | undefined;
      return data?.some((v) => v.status === 'building' || v.status === 'queued') ? 3000 : false;
    },
  });

  async function toggleEnabled() {
    try {
      await apiClient(`/api/admin/agents/${agentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !enabled }),
      });
      toast.success(enabled ? 'Агент отключён' : 'Агент включён');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  return (
    <DrawerSheet paramName="drawer" paramValue={agentId} title={agentName}>
      <div className="space-y-6">
        <div className="space-y-1 text-sm">
          <div>
            <span className="text-[color:var(--color-text-secondary)]">slug:</span>{' '}
            <code className="font-mono">{agentSlug}</code>
          </div>
          <div className="break-all">
            <span className="text-[color:var(--color-text-secondary)]">git:</span>{' '}
            <code className="font-mono text-xs">{gitUrl}</code>
          </div>
          <div>
            <span className="text-[color:var(--color-text-secondary)]">статус:</span>{' '}
            <Badge variant={enabled ? 'default' : 'outline'}>{enabled ? 'Включён' : 'Отключён'}</Badge>
            <Button variant="ghost" size="sm" onClick={toggleEnabled} className="ml-2">
              {enabled ? 'Отключить' : 'Включить'}
            </Button>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-serif text-lg">Версии</h3>
            <Button size="sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? 'Отмена' : 'Создать новую'}
            </Button>
          </div>

          {showForm && (
            <CreateAgentVersionForm
              agentId={agentId}
              onCreated={() => {
                setShowForm(false);
                refetch();
              }}
            />
          )}

          <ul className="mt-3 space-y-2">
            {versions?.map((v) => (
              <li
                key={v.id}
                className="rounded-md border border-[color:var(--color-border)] p-3 text-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-xs">{v.git_sha.slice(0, 7)}</code>
                    <Badge
                      variant={
                        v.status === 'ready'
                          ? 'default'
                          : v.status === 'failed'
                          ? 'destructive'
                          : 'outline'
                      }
                    >
                      {v.status}
                    </Badge>
                    {v.is_current && (
                      <Badge variant="outline" className="border-[color:var(--color-success)]">
                        current
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-[color:var(--color-text-secondary)]">
                    {v.build_finished_at
                      ? formatDate(v.build_finished_at)
                      : v.build_started_at
                      ? `started ${formatDate(v.build_started_at)}`
                      : '—'}
                  </span>
                </div>
                <div className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
                  ref: <code className="font-mono">{v.git_ref}</code> · manifest{' '}
                  <code className="font-mono">{v.manifest_version}</code>
                </div>
                {v.build_error && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-[color:var(--color-error)]">
                      Ошибка build
                    </summary>
                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs">{v.build_error}</pre>
                  </details>
                )}
              </li>
            ))}
            {versions?.length === 0 && (
              <li className="text-sm text-[color:var(--color-text-secondary)]">
                Версий пока нет. Создай первую через форму выше.
              </li>
            )}
          </ul>
        </div>
      </div>
    </DrawerSheet>
  );
}
