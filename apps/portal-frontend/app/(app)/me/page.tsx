import Link from 'next/link';
import type { Route } from 'next';
import { apiServer } from '@/lib/api/server';
import type { UserMeOut, UsagePage } from '@/lib/api/types';
import { QuotaCard } from '@/components/me/QuotaCard';
import { UsageHistoryTable } from '@/components/me/UsageHistoryTable';
import { ChangePasswordDialog } from '@/components/me/ChangePasswordDialog';
import { AvatarUploader } from '@/components/me/AvatarUploader';
import { DisplayNameEditor } from '@/components/me/DisplayNameEditor';
import { cn } from '@/lib/utils';

const TABS = [
  { id: 'profile', label: 'Профиль', numeral: 'i.' },
  { id: 'quota', label: 'Квота', numeral: 'ii.' },
  { id: 'history', label: 'История LLM', numeral: 'iii.' },
] as const;

export default async function MePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; cursor?: string }>;
}) {
  const sp = await searchParams;
  const activeTab = (sp.tab ?? 'profile') as (typeof TABS)[number]['id'];

  const me = await apiServer<UserMeOut>('/api/me');
  const usage =
    activeTab === 'history'
      ? await apiServer<UsagePage>(`/api/me/usage${sp.cursor ? `?cursor=${sp.cursor}` : ''}`)
      : null;

  const initials = (me.display_name || me.email)[0]?.toUpperCase() ?? '?';
  const memberSince = new Intl.DateTimeFormat('ru-RU', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(me.created_at));

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      {/* Header — split: identity card on left, tabs on right */}
      <div className="ed-anim-rise mb-12 grid gap-8 lg:grid-cols-[1fr_2fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            ЛИЧНЫЙ КАБИНЕТ
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            {me.display_name || me.email.split('@')[0]}
          </h1>
          <div className="mt-4 flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <span className="ed-meta">
              <span className="text-[color:var(--color-text-tertiary)]">email</span>{' '}
              <code className="text-[color:var(--color-text-primary)]">{me.email}</code>
            </span>
            <span className="ed-meta">
              <span className="text-[color:var(--color-text-tertiary)]">роль</span>{' '}
              <span className="font-mono uppercase text-[color:var(--color-accent)]">
                {me.role}
              </span>
            </span>
            <span className="ed-meta">
              <span className="text-[color:var(--color-text-tertiary)]">с</span>{' '}
              {memberSince}
            </span>
          </div>
        </div>

        {/* Identity stamp / avatar block */}
        <div className="hidden items-center justify-end lg:flex">
          <AvatarUploader hasAvatar={me.has_avatar} initials={initials} />
        </div>
      </div>

      {/* Tabs row — editorial chapter selector */}
      <div className="ed-anim-rise ed-d-2 mb-10 border-t-2 border-b border-[color:var(--color-text-primary)]">
        <div className="flex flex-wrap">
          {TABS.map((tab) => {
            const active = activeTab === tab.id;
            return (
              <Link
                key={tab.id}
                href={`/me?tab=${tab.id}` as Route}
                className={cn(
                  'group flex items-baseline gap-2 border-r border-[color:var(--color-rule-mute)] px-6 py-4 no-underline transition-all last:border-r-0',
                  active
                    ? 'bg-[color:var(--color-text-primary)] text-[color:var(--color-bg-primary)]'
                    : 'text-[color:var(--color-text-primary)] hover:bg-[color:var(--color-bg-tertiary)]',
                )}
              >
                <span
                  className={cn(
                    'font-mono text-xs',
                    active ? 'text-[color:var(--color-paper-tint)]' : 'text-[color:var(--color-text-tertiary)]',
                  )}
                >
                  {tab.numeral}
                </span>
                <span className="font-serif text-base">{tab.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="ed-anim-rise ed-d-3">
        {activeTab === 'profile' && (
          <div className="grid gap-12 md:grid-cols-[1fr_1fr]">
            {/* Identity details */}
            <div>
              <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
                УЧЁТНАЯ ЗАПИСЬ
              </div>
              <h2 className="ed-section mb-6 text-3xl">
                Регистрационные сведения
              </h2>
              <dl className="border-t border-[color:var(--color-text-primary)]">
                <Row label="Email" value={me.email} mono />
                <Row label="Имя для портала" value={<DisplayNameEditor current={me.display_name} />} />
                <Row label="Роль" value={me.role} mono uppercase />
                <Row
                  label="Зарегистрирован"
                  value={new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long' }).format(new Date(me.created_at))}
                />
              </dl>
            </div>

            {/* Security panel */}
            <div>
              <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
                БЕЗОПАСНОСТЬ
              </div>
              <h2 className="ed-section mb-6 text-3xl">
                Доступ
              </h2>
              <div className="border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-6">
                <p className="font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
                  Авторизация по&nbsp;cookie с&nbsp;HttpOnly-флагом и&nbsp;строгой
                  same-site политикой. Сессия обновляется автоматически.
                </p>
                <div className="mt-6">
                  <ChangePasswordDialog />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'quota' && (
          <div>
            {me.quota ? (
              <QuotaCard quota={me.quota} />
            ) : (
              <div className="border border-dashed border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-12 text-center">
                <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
                  КВОТА НЕ НАЗНАЧЕНА
                </div>
                <h3 className="font-serif text-2xl font-bold">
                  LLM-квота для&nbsp;вас ещё не&nbsp;настроена
                </h3>
                <p className="mx-auto mt-3 max-w-md font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
                  Она будет создана автоматически при&nbsp;первой LLM-задаче. Если
                  хотите получить именной лимит&nbsp;— обратитесь к&nbsp;админу&nbsp;НУГ.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && usage && <UsageHistoryTable page={usage} />}
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  uppercase,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  uppercase?: boolean;
}) {
  return (
    <div className="grid grid-cols-[140px_1fr] items-baseline gap-4 border-b border-[color:var(--color-rule-mute)] py-4">
      <dt className="ed-eyebrow">{label}</dt>
      <dd
        className={cn(
          mono ? 'font-mono text-sm' : 'font-serif text-base',
          uppercase && 'uppercase text-[color:var(--color-accent)]',
          'text-[color:var(--color-text-primary)]',
        )}
      >
        {value}
      </dd>
    </div>
  );
}
