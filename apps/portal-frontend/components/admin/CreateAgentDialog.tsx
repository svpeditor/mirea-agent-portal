'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { ApiError } from '@/lib/api/types';

type Mode = 'wizard' | 'zip' | 'git';

interface Props {
  className?: string;
}

// ─── Простой агент через визуальный мастер ──────────────────────────
interface WizardInput {
  id: string;
  type: 'text' | 'textarea' | 'number' | 'checkbox';
  label: string;
  required: boolean;
}

interface WizardOutput {
  id: string;
  type: 'docx' | 'pdf' | 'json' | 'txt' | 'any';
  label: string;
  filename: string;
  primary: boolean;
}

const CATEGORIES = [
  { value: 'научная-работа', label: 'Научная работа' },
  { value: 'учебная', label: 'Учебная' },
  { value: 'организационная', label: 'Организационная' },
] as const;
const DEFAULT_CATEGORY = CATEGORIES[0].value;

export function CreateAgentDialog({ className }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>('wizard');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Git mode
  const [gitUrl, setGitUrl] = useState('');
  const [gitRef, setGitRef] = useState('main');

  // ZIP mode
  const [zipFile, setZipFile] = useState<File | null>(null);

  // Wizard mode
  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('');
  const [category, setCategory] = useState<string>(DEFAULT_CATEGORY);
  const [shortDesc, setShortDesc] = useState('');
  const [useLlm, setUseLlm] = useState(false);
  const [wInputs, setWInputs] = useState<WizardInput[]>([
    { id: 'message', type: 'text', label: 'Сообщение', required: true },
  ]);
  const [wOutputs, setWOutputs] = useState<WizardOutput[]>([
    { id: 'report', type: 'docx', label: 'Отчёт', filename: 'report.docx', primary: true },
  ]);

  function reset() {
    setError(null);
    setGitUrl(''); setGitRef('main'); setZipFile(null);
    setSlug(''); setName(''); setIcon(''); setShortDesc('');
    setCategory(DEFAULT_CATEGORY); setUseLlm(false);
    setWInputs([{ id: 'message', type: 'text', label: 'Сообщение', required: true }]);
    setWOutputs([{ id: 'report', type: 'docx', label: 'Отчёт', filename: 'report.docx', primary: true }]);
  }

  async function onGitSubmit() {
    await apiClient('/api/admin/agents', {
      method: 'POST',
      body: JSON.stringify({ git_url: gitUrl.trim(), git_ref: gitRef.trim() || 'main' }),
    });
  }

  async function onZipSubmit() {
    if (!zipFile) throw new Error('Выбери ZIP-файл');
    const fd = new FormData();
    fd.append('file', zipFile);
    await apiClient('/api/admin/agents/upload', { method: 'POST', body: fd });
  }

  async function onWizardSubmit() {
    await apiClient('/api/admin/agents/from-template', {
      method: 'POST',
      body: JSON.stringify({
        slug: slug.trim(),
        name: name.trim(),
        icon: icon.trim() || null,
        category,
        short_description: shortDesc.trim(),
        inputs: wInputs.filter((i) => i.id && i.label),
        outputs: wOutputs.filter((o) => o.id && o.filename),
        use_llm: useLlm,
      }),
    });
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === 'git') await onGitSubmit();
      else if (mode === 'zip') await onZipSubmit();
      else await onWizardSubmit();
      setOpen(false);
      reset();
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? (e.body?.error?.message ?? e.message) : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          className ??
          'ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-5 py-2.5 text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)]'
        }
      >
        + Создать агент
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-12"
          onClick={() => !submitting && setOpen(false)}
        >
          <div
            className="w-full max-w-2xl border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] shadow-[8px_8px_0_0_var(--color-text-primary)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-6 py-3">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-[color:var(--color-bg-primary)]">
                НОВЫЙ АГЕНТ
              </span>
            </div>

            {/* Mode tabs */}
            <div className="flex border-b-2 border-[color:var(--color-text-primary)]">
              {([
                ['wizard', 'Мастер'],
                ['zip', 'ZIP-архив'],
                ['git', 'Git URL'],
              ] as [Mode, string][]).map(([m, lbl]) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`flex-1 border-r-2 border-[color:var(--color-text-primary)] py-3 font-mono text-xs uppercase tracking-wider last:border-r-0 ${
                    mode === m
                      ? 'bg-[color:var(--color-text-primary)] text-[color:var(--color-bg-primary)]'
                      : 'hover:bg-[color:var(--color-bg-tertiary)]'
                  }`}
                >
                  {lbl}
                </button>
              ))}
            </div>

            <form onSubmit={onSubmit} className="space-y-4 p-6">
              {mode === 'wizard' && (
                <>
                  <p className="ed-meta">
                    Заполни форму — портал сам сгенерирует boilerplate скелет агента
                    (manifest.yaml + agent.py + Dockerfile) и соберёт его. Можно потом
                    скачать через git/file-store и доработать.
                  </p>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="block">
                      <span className="ed-eyebrow mb-1 block">Slug (id)</span>
                      <input
                        type="text" required value={slug}
                        onChange={(e) => setSlug(e.target.value.toLowerCase())}
                        placeholder="my-agent"
                        pattern="[a-z][a-z0-9-]*"
                        className="ed-input w-full"
                      />
                    </label>
                    <label className="block">
                      <span className="ed-eyebrow mb-1 block">Название</span>
                      <input
                        type="text" required value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Мой агент"
                        className="ed-input w-full"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-[1fr_2fr] gap-3">
                    <label className="block">
                      <span className="ed-eyebrow mb-1 block">Иконка</span>
                      <input
                        type="text" value={icon}
                        onChange={(e) => setIcon(e.target.value)}
                        placeholder="📊"
                        className="ed-input w-full"
                      />
                    </label>
                    <label className="block">
                      <span className="ed-eyebrow mb-1 block">Категория</span>
                      <select
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="ed-input w-full"
                      >
                        {CATEGORIES.map((c) => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label className="block">
                    <span className="ed-eyebrow mb-1 block">Краткое описание</span>
                    <textarea
                      required value={shortDesc}
                      onChange={(e) => setShortDesc(e.target.value)}
                      rows={2}
                      placeholder="Что делает агент — будет видно в каталоге"
                      className="ed-input w-full"
                    />
                  </label>

                  <details className="border border-[color:var(--color-rule-mute)] p-3">
                    <summary className="cursor-pointer font-mono text-xs uppercase tracking-wider">
                      Входы ({wInputs.length})
                    </summary>
                    <div className="mt-2 space-y-2">
                      {wInputs.map((inp, i) => (
                        <div key={i} className="grid grid-cols-[1fr_1fr_2fr_auto] gap-2 items-center">
                          <input
                            type="text" value={inp.id}
                            onChange={(e) => {
                              setWInputs(wInputs.map((it, j) => j === i ? { ...it, id: e.target.value.toLowerCase() } : it));
                            }}
                            placeholder="id"
                            className="ed-input"
                          />
                          <select
                            value={inp.type}
                            onChange={(e) => {
                              setWInputs(wInputs.map((it, j) => j === i ? { ...it, type: e.target.value as WizardInput['type'] } : it));
                            }}
                            className="ed-input"
                          >
                            <option value="text">text</option>
                            <option value="textarea">textarea</option>
                            <option value="number">number</option>
                            <option value="checkbox">checkbox</option>
                          </select>
                          <input
                            type="text" value={inp.label}
                            onChange={(e) => {
                              setWInputs(wInputs.map((it, j) => j === i ? { ...it, label: e.target.value } : it));
                            }}
                            placeholder="Подпись"
                            className="ed-input"
                          />
                          <button
                            type="button"
                            onClick={() => setWInputs(wInputs.filter((_, j) => j !== i))}
                            className="px-2 text-[color:var(--color-error)]"
                          >×</button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => setWInputs([...wInputs, { id: '', type: 'text', label: '', required: false }])}
                        className="font-mono text-xs uppercase tracking-wider hover:text-[color:var(--color-accent)]"
                      >+ Добавить вход</button>
                    </div>
                  </details>

                  <details className="border border-[color:var(--color-rule-mute)] p-3" open>
                    <summary className="cursor-pointer font-mono text-xs uppercase tracking-wider">
                      Выходы ({wOutputs.length})
                    </summary>
                    <div className="mt-2 space-y-2">
                      {wOutputs.map((out, i) => (
                        <div key={i} className="grid grid-cols-[1fr_1fr_1fr_1fr_auto] gap-2 items-center">
                          <input
                            type="text" value={out.id}
                            onChange={(e) => {
                              setWOutputs(wOutputs.map((it, j) => j === i ? { ...it, id: e.target.value.toLowerCase() } : it));
                            }}
                            placeholder="id"
                            className="ed-input"
                          />
                          <select
                            value={out.type}
                            onChange={(e) => {
                              setWOutputs(wOutputs.map((it, j) => j === i ? { ...it, type: e.target.value as WizardOutput['type'] } : it));
                            }}
                            className="ed-input"
                          >
                            <option value="docx">docx</option>
                            <option value="pdf">pdf</option>
                            <option value="json">json</option>
                            <option value="txt">txt</option>
                            <option value="any">any</option>
                          </select>
                          <input
                            type="text" value={out.label}
                            onChange={(e) => {
                              setWOutputs(wOutputs.map((it, j) => j === i ? { ...it, label: e.target.value } : it));
                            }}
                            placeholder="Подпись"
                            className="ed-input"
                          />
                          <input
                            type="text" value={out.filename}
                            onChange={(e) => {
                              setWOutputs(wOutputs.map((it, j) => j === i ? { ...it, filename: e.target.value } : it));
                            }}
                            placeholder="result.docx"
                            className="ed-input"
                          />
                          <button
                            type="button"
                            onClick={() => setWOutputs(wOutputs.filter((_, j) => j !== i))}
                            className="px-2 text-[color:var(--color-error)]"
                          >×</button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => setWOutputs([...wOutputs, { id: '', type: 'docx', label: '', filename: '', primary: false }])}
                        className="font-mono text-xs uppercase tracking-wider hover:text-[color:var(--color-accent)]"
                      >+ Добавить выход</button>
                    </div>
                  </details>

                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
                    <span className="font-mono text-xs uppercase tracking-wider">
                      Агенту нужен LLM (DeepSeek-R1 / Claude Haiku)
                    </span>
                  </label>
                </>
              )}

              {mode === 'zip' && (
                <>
                  <p className="ed-meta">
                    Загрузи ZIP-архив с готовым агентом. В корне должен быть{' '}
                    <code className="font-mono">manifest.yaml</code> + код агента. Если архив обёрнут
                    в одну top-папку — портал её развернёт автоматически.
                  </p>
                  <label className="block">
                    <span className="ed-eyebrow mb-2 block">ZIP-файл</span>
                    <input
                      type="file" accept=".zip"
                      onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
                      className="ed-input w-full"
                    />
                  </label>
                  <p className="ed-meta italic text-[color:var(--color-text-tertiary)]">
                    Макс. 50 МБ. После загрузки портал прочитает manifest и соберёт Docker-образ —
                    это занимает 30-60 секунд.
                  </p>
                </>
              )}

              {mode === 'git' && (
                <>
                  <p className="ed-meta">
                    Платформа клонирует репозиторий, читает manifest.yaml и собирает Docker-образ.
                    Манифест должен лежать в корне репо.
                  </p>
                  <label className="block">
                    <span className="ed-eyebrow mb-2 block">Git URL</span>
                    <input
                      type="url" required={mode === 'git'}
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      placeholder="https://github.com/svpeditor/my-agent.git"
                      className="ed-input w-full"
                    />
                  </label>
                  <label className="block">
                    <span className="ed-eyebrow mb-2 block">Git ref</span>
                    <input
                      type="text" value={gitRef}
                      onChange={(e) => setGitRef(e.target.value)}
                      placeholder="main"
                      className="ed-input w-full"
                    />
                  </label>
                </>
              )}

              {error && (
                <div className="border border-[color:var(--color-error)] bg-[color:var(--color-bg-tertiary)] p-3 font-serif text-sm text-[color:var(--color-error)]">
                  {error}
                </div>
              )}

              <div className="flex justify-end gap-3 border-t border-[color:var(--color-text-primary)] pt-4">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  disabled={submitting}
                  className="px-4 py-2 font-mono text-xs uppercase tracking-wider hover:text-[color:var(--color-accent)] disabled:opacity-50"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-5 py-2 text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)] disabled:opacity-50"
                >
                  {submitting ? 'СОЗДАНИЕ…' : 'СОЗДАТЬ'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
