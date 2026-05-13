import Link from 'next/link';
import type { Route } from 'next';
import { ArrowUpRight, Beaker, Microscope, Send } from 'lucide-react';

interface PublicCatalogAgent {
  slug: string;
  name: string;
  short_description: string;
  icon: string | null;
  category: string;
  category_slug: string;
}

interface PublicCatalogOut {
  agents: PublicCatalogAgent[];
  total_agents: number;
}

async function fetchCatalog(): Promise<PublicCatalogOut> {
  const apiBase = process.env.API_BASE_URL ?? 'http://localhost:8000';
  try {
    const res = await fetch(`${apiBase}/api/public/catalog?limit=3`, {
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`status ${res.status}`);
    return (await res.json()) as PublicCatalogOut;
  } catch {
    // Если API лежит — landing всё равно должен открываться.
    return { agents: [], total_agents: 0 };
  }
}

function staticNumbers(totalAgents: number) {
  return [
    { value: String(totalAgents || '—'), label: 'агентов в реестре' },
    { value: '5—15', label: 'минут до результата' },
    { value: '0', label: 'строк кода требуется' },
    { value: '24/7', label: 'через любой браузер' },
  ];
}

export default async function LandingPage() {
  const catalog = await fetchCatalog();
  const ARTICLES = catalog.agents.map((a, i) => ({
    no: String(i + 1).padStart(2, '0'),
    slug: a.slug,
    category: a.category,
    name: a.name,
    icon: a.icon,
    deck: a.short_description.trim(),
  }));
  const NUMBERS = staticNumbers(catalog.total_agents);
  return (
    <div className="min-h-screen bg-[color:var(--color-bg-primary)]">
      {/* ─── Masthead-style top stripe ─────────────────────────────────── */}
      <div className="border-b border-[color:var(--color-border-strong)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 sm:px-8 py-3">
          <span className="ed-meta">
            <span className="text-[color:var(--color-accent)]">§</span> Известия НУГ
            <span className="mx-2 text-[color:var(--color-text-tertiary)]">·</span>
            Том 1 · Выпуск 1 · Москва, 2026
          </span>
          <span className="ed-meta">
            ISSN 0000-0000 · МИРЭА · НУГ ЦТМО
          </span>
        </div>
      </div>

      {/* ─── HERO ─────────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-[1400px] px-4 sm:px-8 pt-16 pb-24">
        {/* Top-left lockup: numeral + label, like a journal article opening */}
        <div className="ed-anim-rise ed-d-1 mb-8 flex items-baseline gap-4">
          <span className="font-mono text-xs tracking-[0.25em] text-[color:var(--color-accent)]">
            ОТ РЕДАКЦИИ
          </span>
          <span className="h-px flex-1 bg-[color:var(--color-rule-mute)]" />
          <span className="ed-meta">04.05.2026</span>
        </div>

        {/* Massive serif headline — stacked, slightly off-grid */}
        <h1 className="ed-display ed-anim-rise ed-d-2 text-[clamp(3.5rem,9vw,9rem)]">
          Известия
        </h1>
        <h1 className="ed-display ed-anim-rise ed-d-3 -mt-3 text-[clamp(3.5rem,9vw,9rem)]">
          <span className="italic text-[color:var(--color-accent)]">научно-учебной</span>
        </h1>
        <h1 className="ed-display ed-anim-rise ed-d-4 -mt-3 text-[clamp(3.5rem,9vw,9rem)]">
          группы.
        </h1>

        {/* Subhead row — split into two columns with rule */}
        <div className="ed-anim-rise ed-d-5 mt-12 grid gap-12 md:grid-cols-[1fr_2fr]">
          <div className="border-l border-[color:var(--color-text-primary)] pl-6">
            <div className="ed-eyebrow mb-3">О ПОРТАЛЕ</div>
            <p className="font-serif text-lg italic leading-relaxed text-[color:var(--color-text-secondary)]">
              «Цифровые технологии в&nbsp;математическом образовании», МИРЭА.
              Платформа запуска AI-агентов для&nbsp;научной экспертизы, поиска
              литературы и&nbsp;учебных задач — без CLI, без Python.
            </p>
          </div>
          <div className="ed-prose ed-drop-cap">
            <p>
              Преподавателям и&nbsp;студентам НУГ — площадка, на&nbsp;которой
              готовые AI-агенты работают на&nbsp;вашем материале. Агент — это
              git-репозиторий с&nbsp;манифестом, собранный в&nbsp;docker-образ.
              Преподаватель загружает работы, нажимает «запустить» и&nbsp;через
              минуту получает Word-отчёт. Студент-разработчик публикует нового
              агента, портал автоматически его подхватывает. Между ними —
              никакой командной строки.
            </p>
          </div>
        </div>

        {/* CTA row */}
        <div className="ed-anim-rise ed-d-6 mt-16 flex flex-wrap items-center gap-6">
          <Link
            href={'/login' as Route}
            className="ed-stamp no-underline"
          >
            <Send className="h-3.5 w-3.5" strokeWidth={2.5} />
            Войти в систему
          </Link>
          <span className="ed-meta max-w-md">
            Доступ предоставляется только по&nbsp;приглашению. Если вы&nbsp;член
            НУГ — попросите ссылку у&nbsp;администратора лаборатории.
          </span>
        </div>
      </section>

      {/* ─── NUMBERS / KPI strip ──────────────────────────────────────── */}
      <section className="border-y border-[color:var(--color-border-strong)] ed-hatch">
        <div className="mx-auto grid max-w-[1400px] grid-cols-2 gap-px md:grid-cols-4">
          {NUMBERS.map((n, i) => (
            <div
              key={n.label}
              className="ed-anim-fade bg-[color:var(--color-bg-primary)] px-6 py-10 text-center"
              style={{ animationDelay: `${0.1 + i * 0.08}s` }}
            >
              <div className="font-serif text-5xl font-bold text-[color:var(--color-text-primary)]">
                {n.value}
              </div>
              <div className="ed-eyebrow mt-3">{n.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── ARTICLES / agent index ───────────────────────────────────── */}
      <section className="mx-auto max-w-[1400px] px-4 sm:px-8 py-24">
        <div className="mb-12 grid gap-8 md:grid-cols-[1fr_2fr]">
          <div>
            <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
              СОДЕРЖАНИЕ ВЫПУСКА
            </div>
            <h2 className="ed-section text-5xl">
              Что<br/>
              сегодня<br/>
              <span className="italic">в&nbsp;портале.</span>
            </h2>
          </div>
          <div className="border-l border-[color:var(--color-rule-mute)] pl-8 pt-2">
            <p className="ed-prose">
              Ниже — отрывок реестра агентов. Полный список доступен после входа
              в&nbsp;систему. Каждый агент — отдельный <em>выпуск</em> со&nbsp;своим
              манифестом, версионностью и&nbsp;историей сборок.
            </p>
          </div>
        </div>

        {/* Articles list — like a journal TOC, not cards */}
        <div className="border-t-2 border-[color:var(--color-text-primary)]">
          {ARTICLES.length === 0 && (
            <div className="ed-anim-rise px-4 sm:px-8 py-16 text-center">
              <div className="ed-eyebrow mb-2 text-[color:var(--color-text-tertiary)]">
                ВЫПУСК В ПЕЧАТИ
              </div>
              <p className="font-serif text-lg italic text-[color:var(--color-text-secondary)]">
                Реестр готовится. Возвращайтесь позже.
              </p>
            </div>
          )}
          {ARTICLES.map((article, i) => (
            <Link
              key={article.slug}
              href={`/agents/${article.slug}` as Route}
              className="group ed-anim-rise grid grid-cols-1 items-start gap-4 border-b border-[color:var(--color-text-primary)] py-10 no-underline transition-colors hover:bg-[color:var(--color-bg-tertiary)] md:grid-cols-[140px_1fr] md:gap-12"
              style={{ animationDelay: `${0.15 + i * 0.08}s` }}
            >
              {/* Number column */}
              <div className="pt-1 md:text-right">
                <div className="font-serif text-3xl font-bold leading-none tabular-nums text-[color:var(--color-text-primary)] md:text-4xl">
                  №&nbsp;{article.no}
                </div>
              </div>

              {/* Main column */}
              <div className="min-w-0">
                <div className="ed-eyebrow mb-3">{article.category}</div>
                <h3 className="ed-display text-3xl md:text-4xl">
                  {article.name}
                </h3>
                <p className="mt-4 max-w-2xl font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
                  {article.deck}
                </p>
                <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1">
                  <span className="ed-meta">
                    <span className="text-[color:var(--color-text-tertiary)]">·</span>{' '}
                    /{article.slug}
                  </span>
                </div>
              </div>

            </Link>
          ))}
        </div>
      </section>

      {/* ─── EDITORIAL FOOTNOTE ───────────────────────────────────────── */}
      <section className="border-t border-[color:var(--color-border-strong)] bg-[color:var(--color-bg-secondary)]">
        <div className="mx-auto grid max-w-[1400px] gap-12 px-4 sm:px-8 py-16 md:grid-cols-[2fr_1fr]">
          <div>
            <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
              ПОЯСНЕНИЕ
            </div>
            <h2 className="ed-section mb-6 text-3xl">
              Как это устроено технически
            </h2>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="border-l-2 border-[color:var(--color-accent)] pl-4">
                <div className="ed-eyebrow mb-1">i.</div>
                <div className="font-serif text-lg leading-snug">Манифест</div>
                <p className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
                  YAML с&nbsp;описанием inputs, outputs, runtime. Контракт между
                  студентом-разработчиком и&nbsp;порталом.
                </p>
              </div>
              <div className="border-l-2 border-[color:var(--color-accent)] pl-4">
                <div className="ed-eyebrow mb-1">ii.</div>
                <div className="font-serif text-lg leading-snug">Сборка</div>
                <p className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
                  Портал клонирует репозиторий, генерирует Dockerfile,
                  собирает образ. Воркер ставит его в&nbsp;очередь.
                </p>
              </div>
              <div className="border-l-2 border-[color:var(--color-accent)] pl-4">
                <div className="ed-eyebrow mb-1">iii.</div>
                <div className="font-serif text-lg leading-snug">Запуск</div>
                <p className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
                  Контейнер изолирован, видит только входные файлы.
                  WebSocket-стрим показывает прогресс в&nbsp;реальном времени.
                </p>
              </div>
              <div className="border-l-2 border-[color:var(--color-accent)] pl-4">
                <div className="ed-eyebrow mb-1">iv.</div>
                <div className="font-serif text-lg leading-snug">Результат</div>
                <p className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
                  Word, PDF или&nbsp;ZIP. Скачивается одним кликом, остаётся
                  в&nbsp;истории запусков.
                </p>
              </div>
            </div>
          </div>

          <aside className="border-l border-[color:var(--color-rule-mute)] pl-8">
            <div className="ed-eyebrow mb-3">КОЛОФОН</div>
            <div className="font-serif text-base leading-relaxed">
              <strong>Известия НУГ</strong>{' '}
              <em>«Цифровые технологии в&nbsp;математическом образовании»</em>.
              Издаётся при поддержке РТУ&nbsp;МИРЭА, Москва. Главный
              редактор&nbsp;— научный руководитель НУГ.
            </div>
            <div className="mt-6 flex items-baseline gap-3">
              <Beaker className="h-4 w-4 text-[color:var(--color-accent)]" strokeWidth={1.5} />
              <Microscope className="h-4 w-4 text-[color:var(--color-text-secondary)]" strokeWidth={1.5} />
              <span className="ed-meta ml-auto">
                <span className="text-[color:var(--color-accent)]">§</span> 0001
              </span>
            </div>
          </aside>
        </div>
      </section>

      {/* ─── FOOTER ───────────────────────────────────────────────────── */}
      <footer className="border-t-4 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 sm:px-8 py-6">
          <div className="ed-meta">
            <span className="text-[color:var(--color-accent)]">©</span> 2026 НУГ
            ЦТМО · МИРЭА · Москва
          </div>
          <Link
            href={'/login' as Route}
            className="group flex items-center gap-2 ed-meta no-underline hover:text-[color:var(--color-accent)]"
          >
            Войти
            <ArrowUpRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
