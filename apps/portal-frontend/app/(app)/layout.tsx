import type { Route } from 'next';
import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/lib/auth/current-user';
import { Topbar } from '@/components/topbar';
import { CommandPalette } from '@/components/CommandPalette';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) {
    redirect('/login' as Route);
  }
  return (
    <div className="min-h-screen">
      <Topbar user={user} showAdminLink={user.role === 'admin'} />
      <CommandPalette isAdmin={user.role === 'admin'} />
      {/* No inner max-w/padding here — каждая страница сама задаёт layout
          под editorial-разворот (max-w-[1400px] px-8 py-X). */}
      <main>{children}</main>
    </div>
  );
}
