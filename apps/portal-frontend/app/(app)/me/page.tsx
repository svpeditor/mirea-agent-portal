import { apiServer } from '@/lib/api/server';
import type { UserMeOut, UsagePage } from '@/lib/api/types';
import type { Route } from 'next';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QuotaCard } from '@/components/me/QuotaCard';
import { UsageHistoryTable } from '@/components/me/UsageHistoryTable';
import { ChangePasswordDialog } from '@/components/me/ChangePasswordDialog';

export default async function MePage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string; cursor?: string }>;
}) {
  const sp = await searchParams;
  const activeTab = sp.tab ?? 'profile';

  const me = await apiServer<UserMeOut>('/api/me');
  const usage =
    activeTab === 'history'
      ? await apiServer<UsagePage>(`/api/me/usage${sp.cursor ? `?cursor=${sp.cursor}` : ''}`)
      : null;

  return (
    <div>
      <h1 className="mb-6 font-serif text-3xl">Профиль</h1>

      <Tabs value={activeTab}>
        <TabsList>
          <TabsTrigger value="profile" asChild>
            <a href={'/me?tab=profile' as Route} className="no-underline">Профиль</a>
          </TabsTrigger>
          <TabsTrigger value="quota" asChild>
            <a href={'/me?tab=quota' as Route} className="no-underline">Квота</a>
          </TabsTrigger>
          <TabsTrigger value="history" asChild>
            <a href={'/me?tab=history' as Route} className="no-underline">История LLM</a>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6 space-y-4">
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-[color:var(--color-text-secondary)]">Email</dt>
              <dd>{me.email}</dd>
            </div>
            <div>
              <dt className="text-[color:var(--color-text-secondary)]">Имя</dt>
              <dd>{me.display_name}</dd>
            </div>
            <div>
              <dt className="text-[color:var(--color-text-secondary)]">Роль</dt>
              <dd className="font-mono">{me.role}</dd>
            </div>
          </dl>
          <ChangePasswordDialog />
        </TabsContent>

        <TabsContent value="quota" className="mt-6">
          {me.quota ? (
            <QuotaCard quota={me.quota} />
          ) : (
            <p className="text-[color:var(--color-text-secondary)]">
              Квота не настроена. Обратись к админу.
            </p>
          )}
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          {usage && <UsageHistoryTable page={usage} />}
        </TabsContent>
      </Tabs>
    </div>
  );
}
