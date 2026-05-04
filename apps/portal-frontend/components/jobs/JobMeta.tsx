import type { JobDetailOut } from '@/lib/api/types';
import { formatDate } from '@/lib/format';

export function JobMeta({ job }: { job: JobDetailOut }) {
  return (
    <div className="border border-[color:var(--color-text-primary)] bg-[color:var(--color-bg-tertiary)]">
      <div className="border-b border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-4 py-2">
        <span className="font-mono text-[0.6rem] uppercase tracking-[0.2em] text-[color:var(--color-bg-primary)]">
          МЕТАДАННЫЕ ЗАПУСКА
        </span>
      </div>
      <dl className="divide-y divide-[color:var(--color-rule-mute)]">
        <Row label="Создано" value={formatDate(job.created_at)} />
        {job.started_at && <Row label="Запущено" value={formatDate(job.started_at)} />}
        {job.finished_at && <Row label="Завершено" value={formatDate(job.finished_at)} />}
        <Row label="ID" mono value={job.id} />
        {job.error_msg && (
          <div className="px-4 py-3">
            <dt className="ed-eyebrow text-[color:var(--color-error)]">ОШИБКА</dt>
            <dd className="mt-1.5 font-serif text-sm leading-snug text-[color:var(--color-error)]">
              {job.error_msg}
            </dd>
          </div>
        )}
      </dl>

      {/* Params block — collapsed JSON */}
      <details className="border-t border-[color:var(--color-text-primary)] px-4 py-3">
        <summary className="ed-eyebrow cursor-pointer hover:text-[color:var(--color-accent)]">
          ПАРАМЕТРЫ ЗАПУСКА &nbsp;›
        </summary>
        <pre className="mt-3 overflow-x-auto bg-[color:var(--color-bg-secondary)] p-3 font-mono text-xs text-[color:var(--color-text-primary)]">
          {JSON.stringify(job.params, null, 2)}
        </pre>
      </details>

      {job.output_summary && (
        <details className="border-t border-[color:var(--color-text-primary)] px-4 py-3">
          <summary className="ed-eyebrow cursor-pointer hover:text-[color:var(--color-accent)]">
            СВОДКА РЕЗУЛЬТАТА &nbsp;›
          </summary>
          <pre className="mt-3 overflow-x-auto bg-[color:var(--color-bg-secondary)] p-3 font-mono text-xs text-[color:var(--color-text-primary)]">
            {JSON.stringify(job.output_summary, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col px-4 py-2.5 sm:grid sm:grid-cols-[100px_1fr] sm:items-baseline sm:gap-3">
      <dt className="ed-eyebrow">{label}</dt>
      <dd
        className={
          mono
            ? 'font-mono text-xs break-all text-[color:var(--color-text-primary)]'
            : 'font-serif text-sm text-[color:var(--color-text-primary)]'
        }
      >
        {value}
      </dd>
    </div>
  );
}
