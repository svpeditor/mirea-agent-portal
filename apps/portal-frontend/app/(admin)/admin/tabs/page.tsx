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
  return (
    <div>
      <h1 className="mb-6 font-serif text-3xl">Табы</h1>
      <TabsTable tabs={tabs} />
    </div>
  );
}
