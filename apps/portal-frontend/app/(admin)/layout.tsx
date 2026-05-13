import type { Route } from 'next';
import { redirect } from 'next/navigation';
import { getCurrentUser } from '@/lib/auth/current-user';
import { Topbar } from '@/components/topbar';
import { CommandPalette } from '@/components/CommandPalette';
import { AdminSubnav } from '@/components/admin/AdminSubnav';

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect('/login' as Route);
  if (user.role !== 'admin') redirect('/agents' as Route);
  return (
    <div className="min-h-screen">
      <Topbar user={user} showAdminLink />
      <CommandPalette isAdmin />
      {/* Admin breadcrumb / masthead */}
      <div className="border-b border-[color:var(--color-rule-mute)] bg-[color:var(--color-bg-secondary)]">
        <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-3">
          <div className="ed-eyebrow text-[color:var(--color-accent)]">
            <span className="text-[color:var(--color-accent)]">§</span> РЕДАКЦИЯ ИЗВЕСТИЙ — служебная зона
          </div>
        </div>
      </div>
      <AdminSubnav />
      <main>{children}</main>
    </div>
  );
}
