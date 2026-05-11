'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Props {
  /** Если хотя бы один job в состоянии queued/running — авто-обновляться. */
  hasActiveJobs: boolean;
  /** Период опроса в миллисекундах. По умолчанию 5 секунд. */
  intervalMs?: number;
}

const ACTIVE_TIMEOUT_MS = 10 * 60 * 1000; // прекратить через 10 минут idle

export function JobsAutoRefresh({ hasActiveJobs, intervalMs = 5000 }: Props) {
  const router = useRouter();
  useEffect(() => {
    if (!hasActiveJobs) return;
    const stopAt = Date.now() + ACTIVE_TIMEOUT_MS;
    const id = setInterval(() => {
      if (document.hidden) return; // не дёргать в фоне
      if (Date.now() > stopAt) {
        clearInterval(id);
        return;
      }
      router.refresh();
    }, intervalMs);
    return () => clearInterval(id);
  }, [hasActiveJobs, intervalMs, router]);
  return null;
}
