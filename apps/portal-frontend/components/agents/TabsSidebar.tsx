'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { TabOut } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface Props {
  tabs: TabOut[];
  selectedSlug: string | null;
}

// Roman numerals for chapter-style index. Журналы любят римские.
const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];

export function TabsSidebar({ tabs, selectedSlug }: Props) {
  const sortedTabs = [...tabs].sort((a, b) => a.order_idx - b.order_idx);

  return (
    <aside>
      <div className="ed-eyebrow mb-4 text-[color:var(--color-text-tertiary)]">РУБРИКАТОР</div>
      <nav className="border-t border-[color:var(--color-text-primary)]">
        <Link
          href={'/agents' as Route}
          className={cn(
            'group flex items-baseline gap-3 border-b border-[color:var(--color-rule-mute)] py-3 no-underline transition-colors',
            !selectedSlug
              ? 'bg-[color:var(--color-bg-tertiary)] pl-3'
              : 'hover:bg-[color:var(--color-bg-tertiary)] hover:pl-3',
          )}
        >
          <span className="ed-numeral w-7 shrink-0">·</span>
          <span
            className={cn(
              'font-serif text-base leading-tight',
              !selectedSlug ? 'text-[color:var(--color-accent)]' : 'text-[color:var(--color-text-primary)]',
            )}
          >
            Все агенты
          </span>
          {!selectedSlug && (
            <span className="ml-auto pr-2 font-serif text-base text-[color:var(--color-accent)]">
              ←
            </span>
          )}
        </Link>
        {sortedTabs.map((tab, i) => {
          const active = selectedSlug === tab.slug;
          return (
            <Link
              key={tab.id}
              href={`/agents?tab=${tab.slug}` as Route}
              className={cn(
                'group flex items-baseline gap-3 border-b border-[color:var(--color-rule-mute)] py-3 no-underline transition-all',
                active
                  ? 'bg-[color:var(--color-bg-tertiary)] pl-3'
                  : 'hover:bg-[color:var(--color-bg-tertiary)] hover:pl-3',
              )}
            >
              <span className="ed-numeral w-7 shrink-0">{ROMAN[i] ?? `${i + 1}.`}</span>
              <span
                className={cn(
                  'font-serif text-base leading-tight',
                  active
                    ? 'text-[color:var(--color-accent)]'
                    : 'text-[color:var(--color-text-primary)] group-hover:text-[color:var(--color-accent)]',
                )}
              >
                {tab.name}
              </span>
              {active && (
                <span className="ml-auto pr-2 font-serif text-base text-[color:var(--color-accent)]">
                  ←
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Aside helper text */}
      <div className="mt-8 border-l-2 border-[color:var(--color-accent)] pl-4">
        <div className="ed-eyebrow mb-2">КОЛОНТИТУЛ</div>
        <p className="font-serif text-sm leading-relaxed text-[color:var(--color-text-secondary)]">
          Каталог агентов&nbsp;— реестр готовых к&nbsp;запуску инструментов.
          Каждый имеет манифест, версию и&nbsp;историю сборок.
        </p>
      </div>
    </aside>
  );
}
