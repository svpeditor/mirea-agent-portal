'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { JobListItemOut } from '@/lib/api/types';
import { JobStatusBadge } from './JobStatusBadge';
import { formatRelativeTime, formatDuration } from '@/lib/format';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

export function JobsTable({ jobs }: { jobs: JobListItemOut[] }) {
  return (
    <div className="rounded-lg border border-[color:var(--color-border)]">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Задача</TableHead>
            <TableHead>Статус</TableHead>
            <TableHead>Создано</TableHead>
            <TableHead>Длительность</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow key={job.id} className="cursor-pointer">
              <TableCell>
                <Link href={`/jobs/${job.id}` as Route} className="font-mono text-sm no-underline">
                  {job.id.slice(0, 8)}
                </Link>
              </TableCell>
              <TableCell>
                <JobStatusBadge status={job.status} />
              </TableCell>
              <TableCell className="text-sm text-[color:var(--color-text-secondary)]">
                {formatRelativeTime(job.created_at)}
              </TableCell>
              <TableCell className="font-mono text-sm">
                {formatDuration(job.started_at ?? job.created_at, job.finished_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
