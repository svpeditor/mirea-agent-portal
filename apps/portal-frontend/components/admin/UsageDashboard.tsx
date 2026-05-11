'use client';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { UsageBarChart } from './UsageBarChart';
import { formatCurrency } from '@/lib/format';

interface AdminUsageSummary {
  total_cost_usd: string;
  total_requests: number;
  by_user: Array<{ user_id: string; email: string; cost_usd: string; requests: number }>;
  by_agent: Array<{ agent_id: string; slug: string; cost_usd: string; requests: number }>;
  by_model: Array<{ model: string; cost_usd: string; requests: number }>;
}

interface AgentOption {
  id: string;
  slug: string;
  name: string;
}

interface Props {
  summary: AdminUsageSummary;
  agents: AgentOption[];
  selectedAgentId: string | null;
}

export function UsageDashboard({ summary, agents, selectedAgentId }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const totalCost = parseFloat(summary.total_cost_usd) || 0;
  const avg =
    summary.total_requests > 0 ? (totalCost / summary.total_requests).toFixed(6) : '0';

  function setAgentFilter(value: string) {
    const params = new URLSearchParams(searchParams);
    if (value === 'all') params.delete('agent_id');
    else params.set('agent_id', value);
    router.push(`?${params.toString()}` as never);
  }

  return (
    <div className="space-y-8">
      <div className="flex items-end gap-4">
        <div className="w-72">
          <Label htmlFor="agent-filter">Фильтр по агенту</Label>
          <Select value={selectedAgentId ?? 'all'} onValueChange={setAgentFilter}>
            <SelectTrigger id="agent-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все агенты</SelectItem>
              {agents.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.name} ({a.slug})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-[color:var(--color-text-secondary)]">
              Всего стоит
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-3xl">{formatCurrency(summary.total_cost_usd)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-[color:var(--color-text-secondary)]">
              Запросов
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-3xl">
              {summary.total_requests.toLocaleString('ru-RU')}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-[color:var(--color-text-secondary)]">
              В среднем за запрос
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-3xl">{formatCurrency(avg)}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-xl">Топ юзеров</CardTitle>
          </CardHeader>
          <CardContent>
            <UsageBarChart
              bars={summary.by_user.map((u) => ({
                label: u.email,
                value: parseFloat(u.cost_usd) || 0,
                rawString: u.cost_usd,
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-xl">Топ агентов</CardTitle>
          </CardHeader>
          <CardContent>
            <UsageBarChart
              bars={summary.by_agent.map((a) => ({
                label: a.slug,
                value: parseFloat(a.cost_usd) || 0,
                rawString: a.cost_usd,
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="font-serif text-xl">Топ моделей</CardTitle>
          </CardHeader>
          <CardContent>
            <UsageBarChart
              bars={summary.by_model.map((m) => ({
                label: m.model,
                value: parseFloat(m.cost_usd) || 0,
                rawString: m.cost_usd,
              }))}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
