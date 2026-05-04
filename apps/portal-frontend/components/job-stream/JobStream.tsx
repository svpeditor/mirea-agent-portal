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

const TERMINAL_STATUSES: JobStatus[] = ['ready', 'succeeded', 'failed', 'cancelled', 'timed_out'];

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
    <div>
      {/* Live progress strip — only while running */}
      {!terminal && (
        <div className="mb-6 border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-primary)] p-5">
          <div className="mb-4 flex items-baseline justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  connected
                    ? 'bg-[color:var(--color-forest)] [animation:ed-fade-in_1.5s_ease-in-out_infinite_alternate]'
                    : 'bg-[color:var(--color-text-tertiary)]'
                }`}
              />
              <span className="ed-eyebrow text-[color:var(--color-text-primary)]">
                {connected ? 'ПРЯМАЯ ТРАНСЛЯЦИЯ' : 'ПЕРЕПОДКЛЮЧЕНИЕ'}
              </span>
            </div>
            <span className="ed-meta">{events.length} событий</span>
          </div>
          <ProgressBar events={events} />
        </div>
      )}

      {/* Event log */}
      <div className="mb-3 flex items-baseline justify-between">
        <span className="ed-eyebrow">ХРОНИКА СОБЫТИЙ</span>
        {terminal && (
          <span className="ed-meta text-[color:var(--color-forest)]">
            ◆ запуск завершён
          </span>
        )}
      </div>
      <EventFeed events={events} />
    </div>
  );
}
