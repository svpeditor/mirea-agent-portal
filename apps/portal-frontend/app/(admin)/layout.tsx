import type { Route } from 'next';
import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/lib/auth/current-user';
import { Topbar } from '@/components/topbar';

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect('/login' as Route);
  if (user.role !== 'admin') redirect('/agents' as Route);
  return (
    <div className="min-h-screen">
      <Topbar user={user} showAdminLink />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 text-sm text-[color:var(--color-text-secondary)]">
          Админка
        </div>
        {children}
      </main>
    </div>
  );
}
