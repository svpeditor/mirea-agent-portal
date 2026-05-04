import { notFound } from 'next/navigation';
import { apiServer } from '@/lib/api/server';
import { ApiError, type JobDetailOut, type JobEventOut } from '@/lib/api/types';
import { JobStream } from '@/components/job-stream/JobStream';
import { JobOutputs } from '@/components/jobs/JobOutputs';
import { JobMeta } from '@/components/jobs/JobMeta';
import { JobStatusBadge } from '@/components/jobs/JobStatusBadge';

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
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl">{job.agent_name}</h1>
          <div className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
            <code className="font-mono">{job.id}</code>
          </div>
        </div>
        <JobStatusBadge status={job.status} />
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
        <div>
          <JobStream jobId={job.id} initialEvents={initialEvents} initialStatus={job.status} />
        </div>
        <aside className="space-y-6">
          <JobMeta job={job} />
          {job.outputs.length > 0 && <JobOutputs outputs={job.outputs} jobId={job.id} />}
        </aside>
      </div>
    </div>
  );
}
