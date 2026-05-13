'use client';
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import type { Route } from 'next';
import { apiClient } from '@/lib/api/client';
import { mapApiError } from '@/lib/api/errors';
import { toast } from 'sonner';
import { ArrowRight } from 'lucide-react';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawNext = searchParams.get('next') ?? '/agents';
  const next = rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '/agents';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      router.push(next as Route);
      router.refresh();
    } catch (err) {
      toast.error(mapApiError(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div>
        <label htmlFor="email" className="ed-eyebrow mb-2 block">
          Корпоративный email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          disabled={submitting}
          placeholder="ivanov@mirea.ru"
          className="ed-input"
        />
      </div>
      <div>
        <label htmlFor="password" className="ed-eyebrow mb-2 block">
          Пароль
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          disabled={submitting}
          className="ed-input"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="ed-stamp group w-full justify-center disabled:opacity-50"
      >
        {submitting ? 'Авторизация…' : (
          <>
            Войти в систему
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" strokeWidth={2.5} />
          </>
        )}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[color:var(--color-bg-primary)]">
      {/* Top thin meta strip */}
      <div className="border-b border-[color:var(--color-rule-mute)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 sm:px-8 py-3">
          <Link href={'/' as Route} className="ed-meta no-underline hover:text-[color:var(--color-accent)]">
            <span className="text-[color:var(--color-accent)]">§</span> Известия НУГ — на&nbsp;главную
          </Link>
          <span className="ed-meta">
            ISSN 0000-0000 · МИРЭА · НУГ ЦТМО
          </span>
        </div>
      </div>

      {/* Main content — two-column editorial spread */}
      <div className="flex-1">
        <div className="mx-auto grid min-h-[calc(100vh-200px)] max-w-[1400px] grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
          {/* Left: editorial intro / brand */}
          <aside className="flex flex-col justify-between border-[color:var(--color-rule-mute)] px-4 sm:px-8 py-16 lg:border-r lg:px-16 lg:py-20">
            <div>
              <div className="ed-eyebrow ed-anim-rise ed-d-1 mb-6 text-[color:var(--color-accent)]">
                АВТОРИЗАЦИЯ
              </div>
              <h1 className="ed-display ed-anim-rise ed-d-2 text-6xl md:text-7xl">
                Вход<br/>
                <span className="italic text-[color:var(--color-accent)]">в&nbsp;портал</span>
              </h1>
              <p className="ed-anim-rise ed-d-3 mt-8 max-w-md font-serif text-lg leading-relaxed text-[color:var(--color-text-secondary)]">
                Доступ предоставляется только членам научно-учебной группы.
                Если у&nbsp;вас нет учётной записи — попросите ссылку-приглашение
                у&nbsp;администратора лаборатории.
              </p>
            </div>

            <div className="ed-anim-fade ed-d-5 mt-12 grid grid-cols-2 gap-x-6 gap-y-3 lg:mt-0">
              <div>
                <div className="ed-eyebrow text-[color:var(--color-text-tertiary)]">издатель</div>
                <div className="font-serif text-base">РТУ&nbsp;МИРЭА</div>
              </div>
              <div>
                <div className="ed-eyebrow text-[color:var(--color-text-tertiary)]">подразделение</div>
                <div className="font-serif text-base">НУГ ЦТМО</div>
              </div>
              <div>
                <div className="ed-eyebrow text-[color:var(--color-text-tertiary)]">том</div>
                <div className="font-mono text-sm">I</div>
              </div>
              <div>
                <div className="ed-eyebrow text-[color:var(--color-text-tertiary)]">издаётся с</div>
                <div className="font-mono text-sm">2026</div>
              </div>
            </div>
          </aside>

          {/* Right: form panel */}
          <main className="flex items-center justify-center bg-[color:var(--color-bg-tertiary)] px-4 sm:px-8 py-16 lg:px-16">
            <div className="w-full max-w-md">
              <div className="ed-anim-rise ed-d-3 mb-2 flex items-baseline justify-between">
                <span className="ed-eyebrow">ФОРМА I</span>
                <span className="ed-meta">требуется учётная запись</span>
              </div>
              <div className="ed-anim-rule ed-d-4 mb-10 h-px bg-[color:var(--color-text-primary)]" />

              <div className="ed-anim-rise ed-d-5">
                <Suspense
                  fallback={
                    <div className="space-y-8">
                      <div className="h-12 animate-pulse bg-[color:var(--color-bg-secondary)]" />
                      <div className="h-12 animate-pulse bg-[color:var(--color-bg-secondary)]" />
                      <div className="h-12 animate-pulse bg-[color:var(--color-bg-secondary)]" />
                    </div>
                  }
                >
                  <LoginForm />
                </Suspense>
              </div>

              <div className="ed-anim-fade ed-d-7 mt-10 border-t border-[color:var(--color-rule-mute)] pt-6">
                <p className="ed-meta">
                  Ещё не зарегистрированы?{' '}
                  <Link
                    href={'/' as Route}
                    className="text-[color:var(--color-accent)] no-underline hover:underline"
                  >
                    Свяжитесь с&nbsp;администратором НУГ →
                  </Link>
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-[color:var(--color-border-strong)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-4 sm:px-8 py-3">
          <div className="ed-meta">
            <span className="text-[color:var(--color-accent)]">©</span> 2026 НУГ ЦТМО · МИРЭА
          </div>
          <div className="ed-meta">
            <span className="text-[color:var(--color-accent)]">§</span> Форма входа · v1.3
          </div>
        </div>
      </footer>
    </div>
  );
}
