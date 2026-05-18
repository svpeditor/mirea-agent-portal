'use client';
import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import type { LlmSettingsMasked } from '@/app/(admin)/admin/llm-settings/page';

const SECRET_FIELDS = [
  { key: 'openrouter_api_key', label: 'OpenRouter API key', primary: true },
  { key: 'openai_api_key', label: 'OpenAI API key', primary: false },
  { key: 'google_api_key', label: 'Google API key', primary: false },
  { key: 'xai_api_key', label: 'xAI (Grok) API key', primary: false },
  { key: 'anthropic_api_key', label: 'Anthropic API key', primary: false },
  { key: 'deepseek_api_key', label: 'DeepSeek API key', primary: false },
] as const;

type SecretKey = (typeof SECRET_FIELDS)[number]['key'];

export function LlmSettingsForm({ initial }: { initial: LlmSettingsMasked }) {
  const router = useRouter();
  const [vals, setVals] = React.useState<Record<string, string>>({});
  const [cleared, setCleared] = React.useState<Record<string, boolean>>({});
  const [mode, setMode] = React.useState(initial.provider_mode);
  const [models, setModels] = React.useState(
    initial.allowed_models_source === 'db' ? initial.allowed_models : '',
  );
  const [saving, setSaving] = React.useState(false);

  function meta(k: SecretKey) {
    const m = initial[k];
    return m.set
      ? `текущий: ${m.preview}${m.source ? ` (${m.source})` : ''}`
      : 'не задан';
  }

  async function save() {
    const patch: Record<string, string> = { provider_mode: mode };
    for (const { key } of SECRET_FIELDS) {
      const v = (vals[key] ?? '').trim();
      if (cleared[key]) patch[key] = '';
      else if (v) patch[key] = v;
    }
    // allowed_models: пусто => не трогаем; явный сброс — через кнопку ниже
    if (models.trim()) patch.allowed_models = models.trim();
    setSaving(true);
    try {
      await apiClient('/api/admin/llm-settings', {
        method: 'PUT',
        body: JSON.stringify(patch),
      });
      toast.success('Настройки LLM сохранены');
      setVals({});
      setCleared({});
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Label>Режим подключения</Label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-2 text-sm"
        >
          <option value="openrouter">OpenRouter (один ключ на всё)</option>
          <option value="direct">Напрямую к каждому провайдеру (нужны ключи ниже)</option>
        </select>
        <p className="text-xs text-[color:var(--color-text-tertiary)]">
          «Напрямую»: OpenAI / xAI (Grok) / Google идут прямо к провайдеру
          по ключу ниже (если ключ задан, иначе fallback на OpenRouter).
          Anthropic и DeepSeek в этом режиме всё равно через OpenRouter.
        </p>
      </div>

      {SECRET_FIELDS.map(({ key, label, primary }) => (
        <div key={key} className="space-y-1">
          <Label htmlFor={key}>
            {label}
            {primary && (
              <span className="text-[color:var(--color-accent)]"> (основной)</span>
            )}
          </Label>
          <Input
            id={key}
            type="password"
            autoComplete="off"
            placeholder={cleared[key] ? '— будет сброшен —' : 'новое значение (пусто = не менять)'}
            value={vals[key] ?? ''}
            disabled={cleared[key]}
            onChange={(e) => setVals((p) => ({ ...p, [key]: e.target.value }))}
          />
          <div className="flex items-center justify-between text-xs text-[color:var(--color-text-tertiary)]">
            <span>{meta(key)}</span>
            <button
              type="button"
              className="underline"
              onClick={() =>
                setCleared((p) => ({ ...p, [key]: !p[key] }))
              }
            >
              {cleared[key] ? 'отменить сброс' : 'сбросить'}
            </button>
          </div>
        </div>
      ))}

      <div className="space-y-1">
        <Label htmlFor="allowed_models">
          Whitelist моделей (через запятую; пусто = из env)
        </Label>
        <textarea
          id="allowed_models"
          rows={3}
          value={models}
          onChange={(e) => setModels(e.target.value)}
          placeholder={initial.allowed_models}
          className="block w-full border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-2 py-2 font-mono text-xs"
        />
        <p className="text-xs text-[color:var(--color-text-tertiary)]">
          источник сейчас: {initial.allowed_models_source}. Внимание: на этом
          этапе фактический whitelist берётся из манифеста каждого агента —
          это поле сохраняется, но ещё не применяется к запросам.
        </p>
      </div>

      <Button onClick={save} disabled={saving}>
        {saving ? 'Сохраняю…' : 'Сохранить настройки LLM'}
      </Button>
    </div>
  );
}
