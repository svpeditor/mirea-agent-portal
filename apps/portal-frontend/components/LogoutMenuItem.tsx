'use client';
import { useTransition, forwardRef } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut } from 'lucide-react';
import { DropdownMenuItem } from '@/components/ui/dropdown-menu';

/**
 * Logout-кнопка как DropdownMenuItem. Полностью client-side:
 * - onSelect prevents автозакрытия меню до того как fetch отработал
 * - fetch /api/auth/logout (POST) — backend трёт cookies
 * - router.push('/login') + refresh — перетянуть состояние
 *
 * Раньше был <form action=POST> — submission канселился, потому что
 * dropdown unmount'ит форму при click → "Form submission canceled
 * because the form is not connected".
 */
export const LogoutMenuItem = forwardRef<HTMLDivElement>(function LogoutMenuItem(_props, ref) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  async function onLogout(e: Event) {
    e.preventDefault();
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    } catch {
      /* всё равно редиректим */
    }
    startTransition(() => {
      router.push('/login');
      router.refresh();
    });
  }

  return (
    <DropdownMenuItem
      ref={ref}
      onSelect={onLogout}
      disabled={pending}
      className="rounded-none px-3 py-2 focus:bg-[color:var(--color-bg-secondary)]"
    >
      <span className="flex w-full cursor-pointer items-center text-left text-sm text-[color:var(--color-accent)]">
        <LogOut className="mr-2 h-4 w-4" />
        {pending ? 'Выход…' : 'Выйти'}
      </span>
    </DropdownMenuItem>
  );
});
