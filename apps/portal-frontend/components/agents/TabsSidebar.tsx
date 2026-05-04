'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { TabOut } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface Props {
  tabs: TabOut[];
  selectedSlug: string | null;
}

export function TabsSidebar({ tabs, selectedSlug }: Props) {
  const sortedTabs = [...tabs].sort((a, b) => a.order_idx - b.order_idx);

  return (
    <aside className="space-y-1">
      <Link
        href={'/agents' as Route}
        className={cn(
          'block rounded-md px-3 py-2 text-sm no-underline transition-colors',
          !selectedSlug
            ? 'bg-[color:var(--color-bg-secondary)] font-medium'
            : 'hover:bg-[color:var(--color-bg-secondary)]',
        )}
      >
        Все агенты
      </Link>
      {sortedTabs.map((tab) => (
        <Link
          key={tab.id}
          href={`/agents?tab=${tab.slug}` as Route}
          className={cn(
            'block rounded-md px-3 py-2 text-sm no-underline transition-colors',
            selectedSlug === tab.slug
              ? 'bg-[color:var(--color-bg-secondary)] font-medium'
              : 'hover:bg-[color:var(--color-bg-secondary)]',
          )}
        >
          {tab.name}
        </Link>
      ))}
    </aside>
  );
}
