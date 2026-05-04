import Link from 'next/link';
import type { Route } from 'next';
import { notFound } from 'next/navigation';
import { apiServer } from '@/lib/api/server';
import { ApiError, type JobDetailOut, type JobEventOut } from '@/lib/api/types';
import { JobStream } from '@/components/job-stream/JobStream';
import { JobMeta } from '@/components/jobs/JobMeta';
import { JobStatusBadge } from '@/components/jobs/JobStatusBadge';
import { ArrowLeft } from 'lucide-react';
import { formatDate } from '@/lib/format';

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let job: JobDetailOut;
  let initialEvents: JobEventOut[];
  try {
    [job, initialEvents] = await Promise.all([
      apiServer<JobDetailOut>(`/api/jobs/${id}`),
      apiServer<JobEventOut[]>(`/api/jobs/${id}/events?since=0`),
    ]);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="mx-auto max-w-[1400px] px-8 py-10">
      {/* Breadcrumb */}
      <Link
        href={'/jobs' as Route}
        className="ed-anim-rise ed-meta inline-flex items-center gap-1.5 no-underline hover:text-[color:var(--color-accent)]"
      >
        <ArrowLeft className="h-3 w-3" strokeWidth={2} />
        Все запуски
      </Link>

      {/* Header */}
      <header className="ed-anim-rise ed-d-2 mt-8 mb-10">
        <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
          ЗАПУСК
          <span className="mx-2 text-[color:var(--color-text-tertiary)]">·</span>
          <Link
            href={`/agents/${job.agent.slug}` as Route}
            className="text-[color:var(--color-accent)] no-underline hover:underline"
          >
            {job.agent.name}
          </Link>
        </div>

        <div className="grid items-end gap-6 md:grid-cols-[1fr_auto]">
          <h1 className="ed-display text-4xl md:text-6xl">
            {job.agent.name}
          </h1>
          <JobStatusBadge status={job.status} size="lg" />
        </div>

        <div className="ed-anim-rule ed-d-3 mt-6 h-px bg-[color:var(--color-text-primary)]" />

        <div className="mt-5 flex flex-wrap items-baseline gap-x-8 gap-y-2">
          <span className="ed-meta">
            <span className="text-[color:var(--color-text-tertiary)]">id</span>{' '}
            <code className="text-[color:var(--color-text-primary)]">{job.id}</code>
          </span>
          <span className="ed-meta">
            <span className="text-[color:var(--color-text-tertiary)]">создано</span>{' '}
            {formatDate(job.created_at)}
          </span>
          {job.events_count > 0 && (
            <span className="ed-meta">
              <span className="text-[color:var(--color-text-tertiary)]">событий</span>{' '}
              <span className="font-bold text-[color:var(--color-text-primary)]">
                {job.events_count}
              </span>
            </span>
          )}
        </div>
      </header>

      {/* Two columns */}
      <div className="grid gap-x-12 gap-y-8 lg:grid-cols-[1fr_360px]">
        <div className="ed-anim-rise ed-d-3">
          <JobStream jobId={job.id} initialEvents={initialEvents} initialStatus={job.status} />
        </div>
        <aside className="ed-anim-rise ed-d-4">
          <div className="sticky top-8">
            <JobMeta job={job} />
          </div>
        </aside>
      </div>
    </div>
  );
}
