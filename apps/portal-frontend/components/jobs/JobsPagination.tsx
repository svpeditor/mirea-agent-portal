'use client';
import Link from 'next/link';
import { useSearchParams, usePathname } from 'next/navigation';
import type { Route } from 'next';
import { ArrowLeft, ArrowRight } from 'lucide-react';

interface Props {
  /** ID последнего job на странице — будет передан как ?cursor для следующей. */
  lastId: string | null;
  /** Есть ли что-то на странице вообще. */
  hasItems: boolean;
  /** Пришло ли ровно столько сколько просили (значит есть следующая страница). */
  hasMore: boolean;
}

export function JobsPagination({ lastId, hasItems, hasMore }: Props) {
  const pathname = usePathname();
  const params = useSearchParams();
  const currentCursor = params.get('cursor');

  function makeHref(cursor: string | null): Route {
    const next = new URLSearchParams(params);
    if (cursor === null) next.delete('cursor');
    else next.set('cursor', cursor);
    const qs = next.toString();
    return `${pathname}${qs ? `?${qs}` : ''}` as Route;
  }

  if (!hasItems) return null;

  return (
    <div className="ed-anim-rise mt-8 flex items-center justify-between border-t border-[color:var(--color-rule-mute)] pt-6">
      {currentCursor ? (
        <Link
          href={makeHref(null)}
          className="ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-4 py-2 text-[color:var(--color-text-primary)] no-underline hover:bg-[color:var(--color-bg-tertiary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2} />
          На первую страницу
        </Link>
      ) : (
        <span />
      )}
      {hasMore && lastId ? (
        <Link
          href={makeHref(lastId)}
          className="ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] px-4 py-2 text-[color:var(--color-text-primary)] no-underline hover:bg-[color:var(--color-bg-tertiary)]"
        >
          Старше
          <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />
        </Link>
      ) : (
        <span className="ed-meta">конец истории</span>
      )}
    </div>
  );
}
