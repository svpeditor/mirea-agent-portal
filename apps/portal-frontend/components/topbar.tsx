import Link from 'next/link';
import type { Route } from 'next';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import type { UserMeOut } from '@/lib/api/types';
import { LogOut, Shield, User as UserIcon } from 'lucide-react';

interface TopbarProps {
  user: UserMeOut;
  showAdminLink?: boolean;
}

function formatQuota(user: UserMeOut): string {
  if (!user.quota) return '';
  const used = parseFloat(user.quota.period_used_usd);
  const limit = parseFloat(user.quota.monthly_limit_usd);
  if (limit > 1000) return '∞';  // admin
  return `$${used.toFixed(2)} / $${limit.toFixed(2)}`;
}

export function Topbar({ user, showAdminLink }: TopbarProps) {
  const quotaStr = formatQuota(user);
  const initials = user.email.slice(0, 2).toUpperCase();

  return (
    <header className="border-b border-[color:var(--color-border)] bg-[color:var(--color-bg-primary)]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-8">
          <Link href={'/agents' as Route} className="flex items-center gap-2 no-underline">
            <span className="font-serif text-xl">Портал НУГ</span>
          </Link>
          <nav className="flex gap-6 text-sm">
            <Link href={'/agents' as Route} className="no-underline hover:text-[color:var(--color-accent)]">
              Агенты
            </Link>
            <Link href={'/jobs' as Route} className="no-underline hover:text-[color:var(--color-accent)]">
              Мои задачи
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {quotaStr && (
            <Link href={'/me' as Route} className="font-mono text-sm text-[color:var(--color-text-secondary)] no-underline">
              {quotaStr}
            </Link>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar>
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={'/me' as Route} className="cursor-pointer no-underline">
                  <UserIcon className="mr-2 h-4 w-4" />
                  Профиль
                </Link>
              </DropdownMenuItem>
              {showAdminLink && (
                <DropdownMenuItem asChild>
                  <Link href={'/admin/users' as Route} className="cursor-pointer no-underline">
                    <Shield className="mr-2 h-4 w-4" />
                    Админка
                  </Link>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <form action="/api/auth/logout" method="POST" className="w-full">
                  <button type="submit" className="flex w-full cursor-pointer items-center text-left">
                    <LogOut className="mr-2 h-4 w-4" />
                    Выйти
                  </button>
                </form>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
