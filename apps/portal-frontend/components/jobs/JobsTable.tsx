'use client';
import Link from 'next/link';
import type { Route } from 'next';
import type { JobListItemOut } from '@/lib/api/types';
import { JobStatusBadge } from './JobStatusBadge';
import { formatRelativeTime, formatDuration, formatCurrency } from '@/lib/format';
import { ArrowUpRight } from 'lucide-react';

// Journal index / TOC styling — one row = one entry. Numbered, hover-affordance, hairline.

export function JobsTable({ jobs }: { jobs: JobListItemOut[] }) {
  return (
    <div className="border-t-2 border-[color:var(--color-text-primary)]">
      {/* Header row */}
      <div className="hidden grid-cols-[60px_1fr_140px_120px_100px_120px_40px] items-baseline gap-4 border-b border-[color:var(--color-rule-mute)] py-3 md:grid">
        <span className="ed-eyebrow text-right">№</span>
        <span className="ed-eyebrow">Агент / ID</span>
        <span className="ed-eyebrow">Создано</span>
        <span className="ed-eyebrow">Длительность</span>
        <span className="ed-eyebrow text-right">Стоимость</span>
        <span className="ed-eyebrow">Статус</span>
        <span></span>
      </div>

      {jobs.map((job, i) => {
        const agentLabel = job.agent_name ?? job.agent_slug ?? null;
        const cost = job.cost_usd_total ?? null;
        return (
          <Link
            key={job.id}
            href={`/jobs/${job.id}` as Route}
            className="group grid grid-cols-1 gap-4 border-b border-[color:var(--color-text-primary)] py-5 no-underline transition-all hover:bg-[color:var(--color-bg-tertiary)] hover:pl-3 md:grid-cols-[60px_1fr_140px_120px_100px_120px_40px] md:items-baseline md:py-4"
          >
            {/* No */}
            <span className="font-mono text-xs text-[color:var(--color-text-tertiary)] md:text-right">
              {String(jobs.length - i).padStart(3, '0')}
            </span>

            {/* Agent / ID */}
            <span className="min-w-0 flex flex-col">
              {agentLabel ? (
                <span className="truncate font-serif text-base font-bold text-[color:var(--color-text-primary)] transition-colors group-hover:text-[color:var(--color-accent)]">
                  {agentLabel}
                </span>
              ) : null}
              <span className="font-mono text-xs text-[color:var(--color-text-tertiary)]">
                {job.id.slice(0, 8)}–{job.id.slice(-4)}
              </span>
            </span>

            {/* Created */}
            <span className="font-serif text-sm italic text-[color:var(--color-text-secondary)]">
              {formatRelativeTime(job.created_at)}
            </span>

            {/* Duration */}
            <span className="font-mono text-sm tabular-nums text-[color:var(--color-text-primary)]">
              {formatDuration(job.started_at ?? job.created_at, job.finished_at)}
            </span>

            {/* Cost */}
            <span className="font-mono text-sm tabular-nums text-right text-[color:var(--color-text-secondary)]">
              {cost !== null ? formatCurrency(cost) : '—'}
            </span>

            {/* Status */}
            <span>
              <JobStatusBadge status={job.status} />
            </span>

            {/* Affordance */}
            <span className="hidden items-center justify-end md:flex">
              <ArrowUpRight
                className="h-4 w-4 text-[color:var(--color-text-tertiary)] transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-[color:var(--color-accent)]"
                strokeWidth={1.5}
              />
            </span>
          </Link>
        );
      })}
    </div>
  );
}
