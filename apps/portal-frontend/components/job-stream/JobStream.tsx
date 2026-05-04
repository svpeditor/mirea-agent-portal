'use client';
import type { JobEventOut, JobStatus } from '@/lib/api/types';

interface Props {
  jobId: string;
  initialEvents: JobEventOut[];
  initialStatus: JobStatus;
}

export function JobStream({ jobId, initialEvents, initialStatus }: Props) {
  return (
    <div className="rounded-lg border border-[color:var(--color-border)] p-4">
      <div className="mb-2 text-sm">
        Job <code className="font-mono">{jobId}</code> · status: <strong>{initialStatus}</strong> · events: {initialEvents.length}
      </div>
      <div className="text-sm text-[color:var(--color-text-secondary)]">
        JobStream placeholder — реализация в T17.
      </div>
    </div>
  );
}
