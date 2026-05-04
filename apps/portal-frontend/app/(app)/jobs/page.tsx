import { apiServer } from '@/lib/api/server';
import type { JobListItemOut } from '@/lib/api/types';
import { JobsTable } from '@/components/jobs/JobsTable';
import { EmptyState } from '@/components/empty-state';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import type { Route } from 'next';

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

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-serif text-3xl">Мои задачи</h1>
        <Button asChild>
          <Link href={'/agents' as Route} className="no-underline">
            Запустить агента
          </Link>
        </Button>
      </div>
      {jobs.length === 0 ? (
        <EmptyState
          title="Пока нет задач"
          description="Перейди в каталог агентов и запусти первую."
          action={
            <Button asChild>
              <Link href={'/agents' as Route} className="no-underline">
                К агентам
              </Link>
            </Button>
          }
        />
      ) : (
        <JobsTable jobs={jobs} />
      )}
    </div>
  );
}
