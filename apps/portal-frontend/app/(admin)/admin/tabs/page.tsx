import { apiServer } from '@/lib/api/server';
import { TabsTable } from '@/components/admin/TabsTable';

interface TabAdminOut {
  id: string;
  slug: string;
  name: string;
  order_idx: number;
  agents_count: number;
}

export default async function AdminTabsPage() {
  const tabs = await apiServer<TabAdminOut[]>('/api/admin/tabs');
  const totalAgents = tabs.reduce((s, t) => s + t.agents_count, 0);

  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-6 sm:py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · III.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Рубрики<br />
            <span className="italic">каталога.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Разделы каталога агентов. Каждый агент привязан к&nbsp;одному разделу
            через&nbsp;<code className="font-mono">manifest.category</code>.
          </p>
        </div>
        <div className="flex items-end justify-end gap-6">
          <div className="text-right">
            <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
              {tabs.length}
            </div>
            <div className="ed-eyebrow">рубрик</div>
          </div>
          <div className="text-right">
            <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-accent)]">
              {totalAgents}
            </div>
            <div className="ed-eyebrow">агентов</div>
          </div>
        </div>
      </div>

      <div className="ed-anim-rise ed-d-2">
        <TabsTable tabs={tabs} />
      </div>
    </div>
  );
}
