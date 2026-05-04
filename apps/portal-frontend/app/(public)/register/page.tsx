import { apiServer } from '@/lib/api/server';
import { ApiError } from '@/lib/api/types';
import { RegisterForm } from './RegisterForm';
import Link from 'next/link';
import type { Route } from 'next';
import { ArrowLeft } from 'lucide-react';

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ invite?: string }>;
}) {
  const { invite } = await searchParams;

  if (!invite) {
    return (
      <ErrorPage
        title="Ссылка-приглашение не указана"
        description="Эта страница требует параметр ?invite=…"
        code="MISSING_INVITE"
      />
    );
  }

  let inviteInfo: { email: string } | null = null;
  try {
    inviteInfo = await apiServer<{ email: string }>(
      `/api/auth/invite-info?token=${encodeURIComponent(invite)}`,
    );
  } catch (err) {
    const code = err instanceof ApiError ? err.body?.error?.code : null;
    const description =
      code === 'invite_expired' || code === 'invite_invalid' || code === 'invite_used'
        ? 'Срок действия приглашения истёк или оно уже использовано. Попроси админа НУГ оформить новое.'
        : 'Не удалось проверить ссылку-приглашение. Возможно, бэкенд недоступен.';
    return (
      <ErrorPage
        title="Приглашение недействительно"
        description={description}
        code={code ?? 'INVITE_INVALID'}
      />
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[color:var(--color-bg-primary)]">
      {/* Top meta strip */}
      <div className="border-b border-[color:var(--color-rule-mute)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-3">
          <Link href={'/' as Route} className="ed-meta no-underline hover:text-[color:var(--color-accent)]">
            <span className="text-[color:var(--color-accent)]">§</span> Известия НУГ — на&nbsp;главную
          </Link>
          <span className="ed-meta">
            ФОРМА II · РЕГИСТРАЦИЯ ПО ПРИГЛАШЕНИЮ
          </span>
        </div>
      </div>

      <div className="flex-1">
        <div className="mx-auto grid min-h-[calc(100vh-200px)] max-w-[1400px] grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
          {/* Left: editorial intro */}
          <aside className="flex flex-col justify-between border-[color:var(--color-rule-mute)] px-8 py-16 lg:border-r lg:px-16 lg:py-20">
            <div>
              <div className="ed-eyebrow ed-anim-rise ed-d-1 mb-6 text-[color:var(--color-accent)]">
                ВЫ ПОЛУЧИЛИ ПРИГЛАШЕНИЕ
              </div>
              <h1 className="ed-display ed-anim-rise ed-d-2 text-6xl md:text-7xl">
                Создание<br/>
                <span className="italic text-[color:var(--color-accent)]">учётной&nbsp;записи.</span>
              </h1>
              <p className="ed-anim-rise ed-d-3 mt-8 max-w-md font-serif text-lg leading-relaxed text-[color:var(--color-text-secondary)]">
                Ссылка одноразовая. После регистрации на&nbsp;этот email вы&nbsp;будете
                автоматически авторизованы и&nbsp;попадёте в&nbsp;каталог агентов.
              </p>
            </div>

            <div className="ed-anim-fade ed-d-5 mt-12 border-t border-[color:var(--color-rule-mute)] pt-6 lg:mt-0">
              <div className="ed-eyebrow mb-2 text-[color:var(--color-text-tertiary)]">
                ПРИГЛАШЁННЫЙ EMAIL
              </div>
              <div className="font-mono text-base font-bold text-[color:var(--color-text-primary)]">
                {inviteInfo.email}
              </div>
            </div>
          </aside>

          {/* Right: form */}
          <main className="flex items-center justify-center bg-[color:var(--color-bg-tertiary)] px-8 py-16 lg:px-16">
            <div className="w-full max-w-md">
              <div className="ed-anim-rise ed-d-3 mb-2 flex items-baseline justify-between">
                <span className="ed-eyebrow">ФОРМА II</span>
                <span className="ed-meta">все поля обязательны</span>
              </div>
              <div className="ed-anim-rule ed-d-4 mb-10 h-px bg-[color:var(--color-text-primary)]" />

              <div className="ed-anim-rise ed-d-5">
                <RegisterForm token={invite} email={inviteInfo.email} />
              </div>
            </div>
          </main>
        </div>
      </div>

      <footer className="border-t border-[color:var(--color-border-strong)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-3">
          <div className="ed-meta">
            <span className="text-[color:var(--color-accent)]">©</span> 2026 НУГ ЦТМО · МИРЭА
          </div>
          <div className="ed-meta">
            <span className="text-[color:var(--color-accent)]">§</span> Регистрация · v1.3
          </div>
        </div>
      </footer>
    </div>
  );
}

function ErrorPage({ title, description, code }: { title: string; description: string; code: string }) {
  return (
    <div className="flex min-h-screen flex-col bg-[color:var(--color-bg-primary)]">
      <div className="border-b border-[color:var(--color-rule-mute)]">
        <div className="mx-auto max-w-[1400px] px-8 py-3">
          <Link href={'/' as Route} className="ed-meta no-underline hover:text-[color:var(--color-accent)]">
            <span className="text-[color:var(--color-accent)]">§</span> Известия НУГ
          </Link>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center px-8">
        <div className="ed-anim-rise mx-auto max-w-2xl text-center">
          <div className="ed-eyebrow mb-6 text-[color:var(--color-accent)]">
            ОШИБКА · {code}
          </div>
          <h1 className="ed-display text-5xl md:text-6xl">{title}</h1>
          <p className="mx-auto mt-8 max-w-lg font-serif text-lg leading-relaxed text-[color:var(--color-text-secondary)]">
            {description}
          </p>
          <Link href={'/' as Route} className="ed-stamp mt-12 inline-flex no-underline">
            <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2.5} />
            На главную
          </Link>
        </div>
      </div>
    </div>
  );
}
