import Link from 'next/link';
import type { Route } from 'next';
import { apiServer } from '@/lib/api/server';
import type { JobListItemOut } from '@/lib/api/types';
import { JobsTable } from '@/components/jobs/JobsTable';

export default async function AdminJobsPage({
  searchParams,
}: {
  searchParams: Promise<{ cursor?: string }>;
}) {
  const sp = await searchParams;
  const query = new URLSearchParams({ limit: '50' });
  if (sp.cursor) query.set('before', sp.cursor);
  const jobs = await apiServer<JobListItemOut[]>(`/api/admin/jobs?${query}`);

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-12">
      <div className="ed-anim-rise mb-10 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            РЕДАКЦИЯ · VII.
          </div>
          <h1 className="ed-display text-6xl md:text-7xl">
            Все<br />
            <span className="italic">запуски.</span>
          </h1>
          <p className="mt-6 max-w-xl ed-meta">
            Все запуски всех пользователей. Для своих — на странице{' '}
            <Link href={'/jobs' as Route} className="underline hover:text-[color:var(--color-accent)]">
              «Мои запуски»
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-col items-end justify-end gap-3">
          <div className="text-right">
            <div className="font-serif text-4xl font-bold tabular-nums text-[color:var(--color-text-primary)]">
              {jobs.length}
            </div>
            <div className="ed-eyebrow">на странице</div>
          </div>
        </div>
      </div>

      {jobs.length === 0 ? (
        <div className="ed-anim-rise border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)] p-16 text-center">
          <div className="ed-eyebrow mb-2 text-[color:var(--color-text-tertiary)]">
            ХРОНИКА ПУСТА
          </div>
          <p className="font-serif text-base italic text-[color:var(--color-text-secondary)]">
            Ни один пользователь ещё не запускал агентов.
          </p>
        </div>
      ) : (
        <div className="ed-anim-rise ed-d-2">
          <JobsTable jobs={jobs} />
        </div>
      )}
    </div>
  );
}
