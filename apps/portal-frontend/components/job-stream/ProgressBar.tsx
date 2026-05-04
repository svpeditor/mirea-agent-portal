'use client';
import type { JobEventOut } from '@/lib/api/types';
import { Progress } from '@/components/ui/progress';

export function ProgressBar({ events }: { events: JobEventOut[] }) {
  const lastProgress = events.filter((e) => e.type === 'progress').slice(-1)[0];
  const value = (lastProgress?.payload as { value?: number } | undefined)?.value ?? 0;
  const message = (lastProgress?.payload as { message?: string } | undefined)?.message;

  if (events.length === 0) return null;

  return (
    <div>
      <Progress value={value * 100} className="h-2" />
      {message && (
        <p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">{message}</p>
      )}
    </div>
  );
}
