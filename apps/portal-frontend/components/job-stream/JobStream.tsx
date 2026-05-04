'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { JobEventOut, JobStatus } from '@/lib/api/types';
import { useJobWebSocket } from './useJobWebSocket';
import { EventFeed } from './EventFeed';
import { ProgressBar } from './ProgressBar';

interface Props {
  jobId: string;
  initialEvents: JobEventOut[];
  initialStatus: JobStatus;
}

const TERMINAL_STATUSES: JobStatus[] = ['succeeded', 'failed', 'cancelled', 'timed_out'];

export function JobStream({ jobId, initialEvents, initialStatus }: Props) {
  const router = useRouter();
  const [terminal, setTerminal] = useState(TERMINAL_STATUSES.includes(initialStatus));

  const { events, connected } = useJobWebSocket({
    jobId,
    initialEvents,
    onTerminal: () => {
      setTerminal(true);
      router.refresh();
    },
  });

  return (
    <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-6">
      {!terminal && (
        <div className="mb-4">
          <ProgressBar events={events} />
          <p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">
            {connected ? '● подключено' : '○ переподключение...'}
          </p>
        </div>
      )}
      <EventFeed events={events} />
    </div>
  );
}
