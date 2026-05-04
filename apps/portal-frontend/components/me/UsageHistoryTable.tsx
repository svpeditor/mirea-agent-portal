'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { UsagePage } from '@/lib/api/types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { formatRelativeTime, formatCurrency } from '@/lib/format';
import { EmptyState } from '@/components/empty-state';

export function UsageHistoryTable({ page }: { page: UsagePage }) {
  if (page.items.length === 0) {
    return (
      <EmptyState
        title="Пока нет вызовов LLM"
        description="История появится когда запустишь агентов с LLM."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-[color:var(--color-border)]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Когда</TableHead>
              <TableHead>Агент</TableHead>
              <TableHead>Модель</TableHead>
              <TableHead className="text-right">Токены</TableHead>
              <TableHead className="text-right">Стоимость</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {page.items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="text-sm">{formatRelativeTime(item.created_at)}</TableCell>
                <TableCell>
                  <Link href={`/jobs/${item.job_id}` as Route} className="no-underline">
                    {item.agent_slug ?? '—'}
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-xs">{item.model}</TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {item.prompt_tokens + item.completion_tokens}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {formatCurrency(item.cost_usd)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {page.next_cursor && (
        <Button asChild variant="outline" className="w-full">
          <Link href={`/me?tab=history&cursor=${page.next_cursor}` as Route} className="no-underline">
            Загрузить ещё
          </Link>
        </Button>
      )}
    </div>
  );
}
