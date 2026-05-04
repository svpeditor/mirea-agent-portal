'use client';
import type { JobEventOut } from '@/lib/api/types';

export function ProgressBar({ events }: { events: JobEventOut[] }) {
  const lastProgress = events.filter((e) => e.type === 'progress').slice(-1)[0];
  const value = (lastProgress?.payload as { value?: number } | undefined)?.value ?? 0;
  const message = (lastProgress?.payload as { message?: string } | undefined)?.message;

  if (events.length === 0) return null;

  const pct = Math.max(0, Math.min(100, value * 100));

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="ed-eyebrow">ПРОГРЕСС</span>
        <span className="font-mono text-xs tabular-nums text-[color:var(--color-text-primary)]">
          {pct.toFixed(0)}%
        </span>
      </div>
      {/* Editorial progress bar — segmented, like a printer's gauge */}
      <div className="relative h-2 w-full overflow-hidden border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)]">
        <div
          className="h-full bg-[color:var(--color-accent)] transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
        {/* Tick marks every 10% */}
        <div className="pointer-events-none absolute inset-0 grid grid-cols-10">
          {Array.from({ length: 9 }).map((_, i) => (
            <span
              key={i}
              className="border-r border-[color:var(--color-bg-primary)] opacity-40"
            />
          ))}
        </div>
      </div>
      {message && (
        <p className="mt-2 font-mono text-xs text-[color:var(--color-text-secondary)]">
          <span className="text-[color:var(--color-text-tertiary)]">›</span> {message}
        </p>
      )}
    </div>
  );
}
