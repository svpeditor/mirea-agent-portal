'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { DrawerSheet } from './DrawerSheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { CreateAgentVersionForm } from './CreateAgentVersionForm';
import { apiClient } from '@/lib/api/client';
import { formatDate } from '@/lib/format';
import { toast } from 'sonner';
import { mapApiError } from '@/lib/api/errors';
import { Trash } from 'lucide-react';

interface AgentVersion {
  id: string;
  git_ref: string;
  git_sha: string;
  manifest_version: string;
  status: 'queued' | 'building' | 'ready' | 'failed';
  build_started_at: string | null;
  build_finished_at: string | null;
  build_error: string | null;
  build_log: string | null;
  is_current: boolean;
}

interface TabOption {
  id: string;
  name: string;
}

interface Props {
  agentId: string;
  agentName: string;
  agentSlug: string;
  gitUrl: string;
  enabled: boolean;
  costCapUsd: string | null;
  tabId: string;
  tabs: TabOption[];
  icon: string | null;
  shortDescription: string;
}

export function AgentVersionDrawer({
  agentId, agentName, agentSlug, gitUrl, enabled, costCapUsd,
  tabId, tabs, icon, shortDescription,
}: Props) {
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [settingCurrentId, setSettingCurrentId] = useState<string | null>(null);
  const [capInput, setCapInput] = useState(costCapUsd ?? '');
  const [savingCap, setSavingCap] = useState(false);
  const [cardName, setCardName] = useState(agentName);
  const [cardIcon, setCardIcon] = useState(icon ?? '');
  const [cardDesc, setCardDesc] = useState(shortDescription);
  const [cardTab, setCardTab] = useState(tabId);
  const [savingCard, setSavingCard] = useState(false);
  const cardDirty =
    cardName !== agentName ||
    cardIcon !== (icon ?? '') ||
    cardDesc !== shortDescription ||
    cardTab !== tabId;

  async function saveCard() {
    if (!cardName.trim() || !cardDesc.trim()) {
      toast.error('Имя и описание не могут быть пустыми');
      return;
    }
    setSavingCard(true);
    try {
      await apiClient(`/api/admin/agents/${agentId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: cardName.trim(),
          icon: cardIcon.trim() === '' ? null : cardIcon.trim(),
          short_description: cardDesc.trim(),
          tab_id: cardTab,
        }),
      });
      toast.success('Карточка агента сохранена');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSavingCard(false);
    }
  }

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

  async function setCurrent(versionId: string) {
    setSettingCurrentId(versionId);
    try {
      await apiClient(`/api/admin/agent_versions/${versionId}/set_current`, {
        method: 'POST',
      });
      toast.success('Версия назначена текущей');
      await refetch();
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSettingCurrentId(null);
    }
  }

  async function deleteAgent() {
    try {
      await apiClient(`/api/admin/agents/${agentId}`, { method: 'DELETE' });
      toast.success('Агент удалён');
      router.push('/admin/agents');
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    }
  }

  async function saveCap() {
    setSavingCap(true);
    try {
      const trimmed = capInput.trim();
      const value = trimmed === '' ? null : trimmed;
      await apiClient(`/api/admin/agents/${agentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ cost_cap_usd: value }),
      });
      toast.success(value === null ? 'Лимит снят' : `Лимит установлен: $${value}`);
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSavingCap(false);
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
            <DeleteAgentDialog agentSlug={agentSlug} onConfirm={deleteAgent} />
          </div>
          <div className="flex items-baseline gap-2 pt-2">
            <span className="text-[color:var(--color-text-secondary)]">лимит, $:</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={capInput}
              onChange={(e) => setCapInput(e.target.value)}
              placeholder="без лимита"
              className="w-28 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 font-mono text-sm"
            />
            <Button size="sm" variant="ghost" onClick={saveCap} disabled={savingCap || capInput === (costCapUsd ?? '')}>
              Сохранить
            </Button>
          </div>
          <div className="text-xs text-[color:var(--color-text-tertiary)]">
            опциональный потолок на стоимость одного запуска этого агента, дополняет per-job квоту юзера
          </div>
        </div>

        <div className="space-y-3 border-t border-[color:var(--color-text-primary)] pt-4">
          <h3 className="font-serif text-lg">Карточка агента</h3>
          <label className="block text-sm">
            <span className="text-[color:var(--color-text-secondary)]">Категория</span>
            <select
              value={cardTab}
              onChange={(e) => setCardTab(e.target.value)}
              className="mt-1 block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 text-sm"
            >
              {tabs.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </label>
          <div className="flex gap-2">
            <label className="block w-20 text-sm">
              <span className="text-[color:var(--color-text-secondary)]">Иконка</span>
              <input
                value={cardIcon}
                onChange={(e) => setCardIcon(e.target.value)}
                placeholder="🔬"
                className="mt-1 block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 text-center text-sm"
              />
            </label>
            <label className="block flex-1 text-sm">
              <span className="text-[color:var(--color-text-secondary)]">Название</span>
              <input
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
                className="mt-1 block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 text-sm"
              />
            </label>
          </div>
          <label className="block text-sm">
            <span className="text-[color:var(--color-text-secondary)]">Краткое описание</span>
            <textarea
              value={cardDesc}
              onChange={(e) => setCardDesc(e.target.value)}
              rows={3}
              className="mt-1 block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-1 text-sm"
            />
          </label>
          <Button size="sm" onClick={saveCard} disabled={savingCard || !cardDirty}>
            {savingCard ? 'Сохраняю...' : 'Сохранить карточку'}
          </Button>
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
                {v.status === 'ready' && !v.is_current && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="mt-2"
                    onClick={() => setCurrent(v.id)}
                    disabled={settingCurrentId === v.id}
                  >
                    {settingCurrentId === v.id ? 'Назначаю...' : 'Сделать текущей'}
                  </Button>
                )}
                {v.build_error && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-[color:var(--color-error)]">
                      Ошибка build: {v.build_error}
                    </summary>
                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-xs">{v.build_log || v.build_error}</pre>
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

function DeleteAgentDialog({
  agentSlug,
  onConfirm,
}: {
  agentSlug: string;
  onConfirm: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [confirmSlug, setConfirmSlug] = useState('');
  const [deleting, setDeleting] = useState(false);

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault();
    if (confirmSlug !== agentSlug) return;
    setDeleting(true);
    try {
      await onConfirm();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setConfirmSlug('');
      }}
    >
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm" className="ml-2">
          <Trash className="mr-2 h-4 w-4" />
          Удалить агента
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Удалить агента</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleConfirm} className="space-y-3">
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Это действие удалит агента вместе с его историей. Чтобы подтвердить, введите slug агента:{' '}
            <code className="font-mono">{agentSlug}</code>
          </p>
          <div>
            <Label htmlFor="confirm-slug">Slug</Label>
            <Input
              id="confirm-slug"
              value={confirmSlug}
              onChange={(e) => setConfirmSlug(e.target.value)}
              placeholder={agentSlug}
              autoComplete="off"
            />
          </div>
          <Button
            type="submit"
            variant="destructive"
            className="w-full"
            disabled={confirmSlug !== agentSlug || deleting}
          >
            {deleting ? 'Удаляю...' : 'Удалить агента'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
