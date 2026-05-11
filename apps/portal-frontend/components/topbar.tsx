import Link from 'next/link';
import type { Route } from 'next';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { UserMeOut } from '@/lib/api/types';
import { Shield, User as UserIcon } from 'lucide-react';
import { LogoutMenuItem } from './LogoutMenuItem';

interface TopbarProps {
  user: UserMeOut;
  showAdminLink?: boolean;
}

const UNLIMITED_QUOTA_THRESHOLD_USD = 1000;

function computeInitials(user: UserMeOut): string {
  if (user.display_name) {
    const parts = user.display_name.trim().split(/\s+/);
    return parts
      .map((p) => p[0] ?? '')
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }
  return (user.email[0] ?? '?').toUpperCase();
}

function formatQuota(user: UserMeOut): string {
  if (!user.quota) return '';
  const used = parseFloat(user.quota.period_used_usd) || 0;
  const limit = parseFloat(user.quota.monthly_limit_usd) || 0;
  if (limit > UNLIMITED_QUOTA_THRESHOLD_USD) return '∞';
  return `$${used.toFixed(2)} / $${limit.toFixed(2)}`;
}

export function Topbar({ user, showAdminLink }: TopbarProps) {
  const quotaStr = formatQuota(user);
  const initials = computeInitials(user);
  const today = new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());

  return (
    <header className="border-b border-[color:var(--color-border-strong)] bg-[color:var(--color-bg-primary)]">
      {/* Date/issue strip — like a newspaper top line */}
      <div className="border-b border-[color:var(--color-rule-mute)]">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-2">
          <span className="ed-meta">
            <span className="text-[color:var(--color-accent)]">§</span> Известия НУГ
            <span className="mx-2 text-[color:var(--color-text-tertiary)]">·</span>
            Том 1 · Москва, {today}
          </span>
          <span className="ed-meta">
            ISSN 0000-0000 · МИРЭА · НУГ ЦТМО
          </span>
        </div>
      </div>

      {/* Main masthead row */}
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-8 py-5">
        <div className="flex items-end gap-12">
          <Link href={'/agents' as Route} className="no-underline">
            <div className="flex items-baseline gap-3">
              <span className="font-serif text-2xl font-bold leading-none text-[color:var(--color-text-primary)]">
                Известия
              </span>
              <span className="font-serif text-2xl italic leading-none text-[color:var(--color-accent)]">
                НУГ
              </span>
            </div>
          </Link>

          <nav className="hidden items-baseline gap-7 text-sm md:flex">
            <Link
              href={'/agents' as Route}
              className="group relative text-[color:var(--color-text-primary)] no-underline"
            >
              <span className="ed-numeral mr-1.5">I.</span>
              Каталог агентов
              <span className="absolute -bottom-1 left-0 h-px w-0 bg-[color:var(--color-accent)] transition-all group-hover:w-full" />
            </Link>
            <Link
              href={'/jobs' as Route}
              className="group relative text-[color:var(--color-text-primary)] no-underline"
            >
              <span className="ed-numeral mr-1.5">II.</span>
              Запуски
              <span className="absolute -bottom-1 left-0 h-px w-0 bg-[color:var(--color-accent)] transition-all group-hover:w-full" />
            </Link>
            {showAdminLink && (
              <Link
                href={'/admin/users' as Route}
                className="group relative text-[color:var(--color-text-primary)] no-underline"
              >
                <span className="ed-numeral mr-1.5">III.</span>
                Редакция
                <span className="absolute -bottom-1 left-0 h-px w-0 bg-[color:var(--color-accent)] transition-all group-hover:w-full" />
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3 md:gap-6">
          {quotaStr && (
            <Link
              href={'/me' as Route}
              className="ed-meta hidden no-underline hover:text-[color:var(--color-accent)] sm:inline-flex"
              title="Месячная квота LLM"
            >
              <span className="text-[color:var(--color-text-tertiary)]">квота</span>{' '}
              {quotaStr}
            </Link>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                aria-label="Меню пользователя"
                className="flex h-10 w-10 items-center justify-center overflow-hidden border border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] font-mono text-xs font-bold text-[color:var(--color-bg-primary)] transition-colors hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)]"
              >
                {user.has_avatar ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`/api/me/avatar?v=${user.avatar_version ?? ''}`}
                    alt="Аватар"
                    className="h-full w-full object-cover"
                  />
                ) : (
                  initials
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-56 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] p-0 [border-radius:0]"
            >
              <div className="border-b border-[color:var(--color-rule-mute)] px-3 pt-3 pb-2">
                <div className="ed-meta">авторизован как</div>
                <div className="font-serif text-base font-bold text-[color:var(--color-text-primary)]">
                  {user.display_name || user.email.split('@')[0]}
                </div>
                <div className="font-mono text-xs text-[color:var(--color-text-secondary)]">
                  {user.email}
                </div>
                {quotaStr && (
                  <div className="mt-1 font-mono text-xs text-[color:var(--color-text-secondary)] sm:hidden">
                    квота {quotaStr}
                  </div>
                )}
              </div>
              {/* Mobile-only nav — на md+ скрыто (есть top nav) */}
              <DropdownMenuItem
                asChild
                className="rounded-none px-3 py-2 focus:bg-[color:var(--color-bg-secondary)] md:hidden"
              >
                <Link
                  href={'/agents' as Route}
                  className="flex cursor-pointer items-center text-sm no-underline"
                >
                  <span className="ed-numeral mr-2 w-4 text-center">I.</span>
                  Каталог агентов
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                asChild
                className="rounded-none px-3 py-2 focus:bg-[color:var(--color-bg-secondary)] md:hidden"
              >
                <Link
                  href={'/jobs' as Route}
                  className="flex cursor-pointer items-center text-sm no-underline"
                >
                  <span className="ed-numeral mr-2 w-4 text-center">II.</span>
                  Запуски
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator className="my-0 bg-[color:var(--color-rule-mute)] md:hidden" />
              <DropdownMenuItem
                asChild
                className="rounded-none px-3 py-2 focus:bg-[color:var(--color-bg-secondary)]"
              >
                <Link
                  href={'/me' as Route}
                  className="flex cursor-pointer items-center text-sm no-underline"
                >
                  <UserIcon className="mr-2 h-4 w-4" />
                  Профиль
                </Link>
              </DropdownMenuItem>
              {showAdminLink && (
                <DropdownMenuItem
                  asChild
                  className="rounded-none px-3 py-2 focus:bg-[color:var(--color-bg-secondary)]"
                >
                  <Link
                    href={'/admin/users' as Route}
                    className="flex cursor-pointer items-center text-sm no-underline"
                  >
                    <Shield className="mr-2 h-4 w-4" />
                    Редакторская
                  </Link>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator className="my-0 bg-[color:var(--color-rule-mute)]" />
              <LogoutMenuItem />
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
