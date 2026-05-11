import Link from 'next/link';
import type { Route } from 'next';
import { apiServer } from '@/lib/api/server';
import type { JobListItemOut } from '@/lib/api/types';
import { JobsTable } from '@/components/jobs/JobsTable';
import { JobsAutoRefresh } from '@/components/jobs/JobsAutoRefresh';
import { JobsFilterBar } from '@/components/jobs/JobsFilterBar';
import { Send } from 'lucide-react';

const FILTER_STATUSES: Record<string, string[]> = {
  active: ['queued', 'running'],
  ready: ['ready'],
  failed: ['failed', 'timed_out'],
  cancelled: ['cancelled'],
};

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ filter?: string; cursor?: string }>;
}) {
  const sp = await searchParams;
  const filter = sp.filter ?? 'all';

  const allJobs = await apiServer<JobListItemOut[]>('/api/jobs?limit=100');

  const counts: Record<string, number> = {};
  for (const j of allJobs) counts[j.status] = (counts[j.status] ?? 0) + 1;

  const allowed = FILTER_STATUSES[filter];
  const jobs = allowed
    ? allJobs.filter((j) => allowed.includes(j.status))
    : allJobs;

  const hasActiveJobs = jobs.some((j) => j.status === 'queued' || j.status === 'running');

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <JobsAutoRefresh hasActiveJobs={hasActiveJobs} />
      {/* Header */}
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РАЗДЕЛ II · ХРОНИКА ЗАПУСКОВ
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Мои<br />
            <span className="italic">запуски.</span>
          </h1>
        </div>
        <div className="flex flex-col items-start justify-end gap-4 md:items-end">
          <p className="ed-meta md:text-right">
            Показано <span className="text-[color:var(--color-text-primary)] font-bold">{jobs.length}</span>
            {' из '}
            <span className="text-[color:var(--color-text-primary)] font-bold">{allJobs.length}</span>
          </p>
          <Link
            href={'/agents' as Route}
            className="ed-stamp no-underline"
          >
            <Send className="h-3.5 w-3.5" strokeWidth={2.5} />
            Новый запуск
          </Link>
        </div>
      </div>

      <JobsFilterBar counts={counts} active={filter} />

      {/* Body */}
      {jobs.length === 0 ? (
        <div className="ed-anim-rise ed-d-2 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-16 text-center">
          <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
            {allJobs.length === 0 ? 'ХРОНИКА ПУСТА' : 'НИЧЕГО НЕ НАЙДЕНО'}
          </div>
          <h2 className="font-serif text-3xl font-bold">
            {allJobs.length === 0 ? 'Запусков ещё не было' : 'По этому фильтру пусто'}
          </h2>
          <p className="mx-auto mt-4 max-w-md font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
            {allJobs.length === 0
              ? 'Перейдите в каталог агентов и запустите первую задачу. Она появится здесь со всеми событиями и результатом.'
              : 'Сними фильтр или попробуй другой статус.'}
          </p>
          <Link href={'/agents' as Route} className="ed-stamp mt-8 inline-flex no-underline">
            <Send className="h-3.5 w-3.5" strokeWidth={2.5} />
            К каталогу
          </Link>
        </div>
      ) : (
        <div className="ed-anim-rise ed-d-2">
          <JobsTable jobs={jobs} />
        </div>
      )}
    </div>
  );
}
