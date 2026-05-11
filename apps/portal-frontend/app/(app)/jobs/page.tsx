import Link from 'next/link';
import type { Route } from 'next';
import { apiServer } from '@/lib/api/server';
import type { JobListItemOut } from '@/lib/api/types';
import { JobsTable } from '@/components/jobs/JobsTable';
import { JobsAutoRefresh } from '@/components/jobs/JobsAutoRefresh';
import { Send } from 'lucide-react';

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; cursor?: string }>;
}) {
  const sp = await searchParams;
  const query = new URLSearchParams();
  if (sp.status) query.set('status', sp.status);
  if (sp.cursor) query.set('cursor', sp.cursor);

  const jobs = await apiServer<JobListItemOut[]>(
    `/api/jobs${query.size ? '?' + query.toString() : ''}`,
  );
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
            Всего <span className="text-[color:var(--color-text-primary)] font-bold">{jobs.length}</span>{' '}
            запусков
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

      {/* Body */}
      {jobs.length === 0 ? (
        <div className="ed-anim-rise ed-d-2 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-16 text-center">
          <div className="ed-eyebrow mb-4 text-[color:var(--color-accent)]">
            ХРОНИКА ПУСТА
          </div>
          <h2 className="font-serif text-3xl font-bold">Запусков ещё не было</h2>
          <p className="mx-auto mt-4 max-w-md font-serif text-base leading-relaxed text-[color:var(--color-text-secondary)]">
            Перейдите в&nbsp;каталог агентов и&nbsp;запустите первую задачу. Она&nbsp;появится
            здесь со&nbsp;всеми событиями и&nbsp;результатом.
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
