import Link from 'next/link';
import type { Route } from 'next';
import { notFound } from 'next/navigation';
import { apiServer } from '@/lib/api/server';
import { ApiError, type AgentDetailOut } from '@/lib/api/types';
import { AgentForm } from '@/components/agent-form/AgentForm';
import { ArrowLeft, Beaker, FileText, Database, Cpu } from 'lucide-react';

interface ManifestRuntime {
  docker?: { base_image?: string };
  llm?: { provider?: string; models?: string[] };
  limits?: {
    max_runtime_minutes?: number;
    max_memory_mb?: number;
    max_cpu_cores?: number;
  };
}

interface ManifestOutput {
  id: string;
  type: string;
  label: string;
  filename: string;
  primary?: boolean;
}

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

  const manifest = agent.manifest as unknown as {
    inputs?: Record<string, unknown>;
    files?: Record<string, unknown>;
    outputs?: ManifestOutput[];
    runtime?: ManifestRuntime;
    about?: string;
  };

  const inputCount = Object.keys(manifest.inputs ?? {}).length;
  const fileCount = Object.keys(manifest.files ?? {}).length;
  const outputs = manifest.outputs ?? [];
  const runtime = manifest.runtime ?? {};
  const llmModels = runtime.llm?.models ?? [];

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-10">
      {/* Breadcrumb / back link */}
      <Link
        href={'/agents' as Route}
        className="ed-anim-rise ed-meta inline-flex items-center gap-1.5 no-underline hover:text-[color:var(--color-accent)]"
      >
        <ArrowLeft className="h-3 w-3" strokeWidth={2} />
        Каталог агентов
      </Link>

      {/* Article header — like opening spread of journal article */}
      <header className="ed-anim-rise ed-d-2 mt-8 mb-12">
        <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
          СТАТЬЯ № {String(Math.abs(hashCode(agent.id)) % 100).padStart(2, '0')}
          <span className="mx-2 text-[color:var(--color-text-tertiary)]">·</span>
          {agent.tab.name}
          <span className="mx-2 text-[color:var(--color-text-tertiary)]">·</span>
          <span className="font-mono">v{agent.current_version.manifest_version}</span>
        </div>

        <h1 className="ed-display text-5xl md:text-7xl">
          {agent.name}
        </h1>

        <div className="ed-anim-rule ed-d-3 mt-8 h-px bg-[color:var(--color-text-primary)]" />

        {/* Byline / metadata strip */}
        <dl className="ed-anim-fade ed-d-4 mt-6 grid grid-cols-2 gap-x-8 gap-y-3 md:grid-cols-4">
          <MetaItem label="Раздел" value={agent.tab.name} />
          <MetaItem label="Slug" value={agent.slug} mono />
          <MetaItem label="Версия" value={`v${agent.current_version.manifest_version}`} mono />
          <MetaItem label="Git SHA" value={agent.current_version.git_sha.slice(0, 7)} mono />
        </dl>
      </header>

      {/* Article body — two columns */}
      <div className="grid gap-x-16 gap-y-12 lg:grid-cols-[1fr_440px]">
        {/* Left: prose + technical specs */}
        <article>
          {/* Abstract */}
          <section className="ed-anim-rise ed-d-3">
            <div className="ed-eyebrow mb-3">АННОТАЦИЯ</div>
            <p className="ed-prose ed-drop-cap">
              {agent.short_description}
            </p>
          </section>

          {/* About body if present */}
          {manifest.about && (
            <section className="ed-anim-rise ed-d-4 mt-12">
              <div className="ed-eyebrow mb-3">ОПИСАНИЕ</div>
              <div
                className="ed-prose"
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {manifest.about}
              </div>
            </section>
          )}

          {/* Technical spec block — like methods section of paper */}
          <section className="ed-anim-rise ed-d-5 mt-16">
            <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
              ТЕХНИЧЕСКИЕ ХАРАКТЕРИСТИКИ
            </div>
            <h2 className="ed-section mb-6 text-3xl">Спецификация</h2>

            <div className="grid grid-cols-1 gap-px overflow-hidden border border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] sm:grid-cols-2">
              <SpecBlock
                Icon={FileText}
                eyebrow="Входы"
                value={inputCount + fileCount}
                detail={
                  <>
                    {inputCount} текстовых, {fileCount} файловых
                  </>
                }
              />
              <SpecBlock
                Icon={Database}
                eyebrow="Артефакты"
                value={outputs.length}
                detail={outputs.map((o) => o.filename).join(', ') || '—'}
              />
              <SpecBlock
                Icon={Cpu}
                eyebrow="Лимиты"
                value={`${runtime.limits?.max_runtime_minutes ?? '—'} мин`}
                detail={
                  <>
                    {runtime.limits?.max_memory_mb ?? '—'} MB ·{' '}
                    {runtime.limits?.max_cpu_cores ?? '—'} CPU
                  </>
                }
              />
              <SpecBlock
                Icon={Beaker}
                eyebrow="Базовый образ"
                value={
                  <span className="font-mono text-base">
                    {runtime.docker?.base_image?.split(':')[0] ?? '—'}
                  </span>
                }
                detail={runtime.docker?.base_image ?? ''}
              />
            </div>

            {llmModels.length > 0 && (
              <div className="mt-8 border-l-2 border-[color:var(--color-accent)] pl-4">
                <div className="ed-eyebrow mb-2">LLM-БЭКЕНД</div>
                <div className="font-serif text-base">
                  Через прокси портала: {runtime.llm?.provider ?? 'OpenRouter'}
                </div>
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                  {llmModels.map((m) => (
                    <span key={m} className="font-mono text-xs text-[color:var(--color-text-secondary)]">
                      <span className="text-[color:var(--color-text-tertiary)]">·</span> {m}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Outputs as sidebar table */}
          {outputs.length > 0 && (
            <section className="ed-anim-rise ed-d-6 mt-16">
              <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
                ВЫХОДНЫЕ АРТЕФАКТЫ
              </div>
              <h2 className="ed-section mb-6 text-3xl">Что получите</h2>
              <ul className="border-t-2 border-[color:var(--color-text-primary)]">
                {outputs.map((output) => (
                  <li
                    key={output.id}
                    className="grid grid-cols-[60px_1fr_auto] gap-4 border-b border-[color:var(--color-rule-mute)] py-4 md:gap-8"
                  >
                    <span className="ed-eyebrow pt-1">
                      {output.type.toUpperCase()}
                    </span>
                    <div>
                      <div className="font-serif text-lg leading-tight">
                        {output.label}
                        {output.primary && (
                          <span className="ml-2 inline-block bg-[color:var(--color-accent)] px-1.5 py-0.5 align-middle font-mono text-[0.6rem] tracking-wider text-[color:var(--color-bg-primary)] uppercase">
                            primary
                          </span>
                        )}
                      </div>
                      <div className="ed-meta mt-1">
                        файл: <code className="text-[color:var(--color-text-primary)]">{output.filename}</code>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </article>

        {/* Right: submission form sidebar (sticky) */}
        <aside className="ed-anim-rise ed-d-4">
          <div className="sticky top-8 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)]">
            {/* Form header — like submission form heading */}
            <div className="border-b border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-6 py-4 text-[color:var(--color-bg-primary)]">
              <div className="font-mono text-[0.65rem] tracking-[0.2em] text-[color:var(--color-paper-tint)] uppercase opacity-70">
                ФОРМА ЗАПУСКА · v{agent.current_version.manifest_version}
              </div>
              <h2 className="font-serif text-2xl font-bold leading-tight">
                Запустить агента
              </h2>
            </div>

            <div className="px-6 py-6">
              <p className="ed-meta mb-6">
                Заполните параметры. После запуска вы&nbsp;будете перенаправлены
                на&nbsp;страницу с&nbsp;живым прогрессом.
              </p>
              <AgentForm manifest={agent.manifest} agentSlug={agent.slug} />
            </div>

            <div className="border-t border-[color:var(--color-rule-mute)] bg-[color:var(--color-bg-secondary)] px-6 py-3 ed-hatch">
              <div className="ed-meta">
                <span className="text-[color:var(--color-accent)]">§</span> Запуск
                использует{' '}
                <span className="font-bold text-[color:var(--color-text-primary)]">
                  {runtime.limits?.max_runtime_minutes ?? '—'} мин
                </span>{' '}
                таймаута и&nbsp;{runtime.limits?.max_memory_mb ?? '—'} MB&nbsp;памяти.
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function MetaItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="ed-eyebrow text-[color:var(--color-text-tertiary)]">{label}</dt>
      <dd
        className={
          mono
            ? 'mt-1 font-mono text-sm text-[color:var(--color-text-primary)]'
            : 'mt-1 font-serif text-base text-[color:var(--color-text-primary)]'
        }
      >
        {value}
      </dd>
    </div>
  );
}

function SpecBlock({
  Icon,
  eyebrow,
  value,
  detail,
}: {
  Icon: typeof Beaker;
  eyebrow: string;
  value: React.ReactNode;
  detail: React.ReactNode;
}) {
  return (
    <div className="bg-[color:var(--color-bg-primary)] p-6">
      <div className="mb-3 flex items-baseline justify-between">
        <span className="ed-eyebrow">{eyebrow}</span>
        <Icon className="h-3.5 w-3.5 text-[color:var(--color-text-tertiary)]" strokeWidth={1.5} />
      </div>
      <div className="font-serif text-3xl font-bold text-[color:var(--color-text-primary)]">
        {value}
      </div>
      <div className="ed-meta mt-1 truncate" title={typeof detail === 'string' ? detail : undefined}>
        {detail}
      </div>
    </div>
  );
}

// Stable hash for article numbering — visual continuity for same agent
function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return h;
}
