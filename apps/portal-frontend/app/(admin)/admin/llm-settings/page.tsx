import { apiServer } from '@/lib/api/server';
import { LlmSettingsForm } from '@/components/admin/LlmSettingsForm';

export interface MaskedSecret {
  set: boolean;
  preview: string;
  source?: string;
}

export interface LlmSettingsMasked {
  provider_mode: string;
  allowed_models: string;
  allowed_models_source: string;
  openrouter_api_key: MaskedSecret;
  openai_api_key: MaskedSecret;
  google_api_key: MaskedSecret;
  xai_api_key: MaskedSecret;
  anthropic_api_key: MaskedSecret;
  deepseek_api_key: MaskedSecret;
}

export default async function AdminLlmSettingsPage() {
  const data = await apiServer<LlmSettingsMasked>('/api/admin/llm-settings');

  return (
    <div className="mx-auto max-w-[900px] px-4 sm:px-8 py-6 sm:py-12">
      <div className="ed-anim-rise mb-10">
        <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
          РЕДАКЦИЯ · VI.
        </div>
        <h1 className="ed-display text-6xl md:text-7xl">
          Ключи<br />
          <span className="italic">LLM.</span>
        </h1>
        <p className="mt-6 max-w-xl ed-meta">
          Ключ OpenRouter и режим подключения. Значения хранятся на сервере,
          в интерфейс не возвращаются — показывается только маска. Пустое
          поле = не менять.
        </p>
      </div>
      <div className="ed-anim-rise ed-d-2">
        <LlmSettingsForm initial={data} />
      </div>
    </div>
  );
}
