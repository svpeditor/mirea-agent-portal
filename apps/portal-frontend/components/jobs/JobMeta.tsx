import type { JobDetailOut } from '@/lib/api/types';
import { formatDate, formatCurrency } from '@/lib/format';

export function JobMeta({ job }: { job: JobDetailOut }) {
  return (
    <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-4">
      <h3 className="mb-3 font-serif text-lg">Параметры</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-[color:var(--color-text-secondary)]">Создано</dt>
          <dd>{formatDate(job.created_at)}</dd>
        </div>
        {job.finished_at && (
          <div>
            <dt className="text-[color:var(--color-text-secondary)]">Завершено</dt>
            <dd>{formatDate(job.finished_at)}</dd>
          </div>
        )}
        <div>
          <dt className="text-[color:var(--color-text-secondary)]">Стоимость LLM</dt>
          <dd className="font-mono">{formatCurrency(job.cost_usd_total)}</dd>
        </div>
        <div>
          <dt className="text-[color:var(--color-text-secondary)]">Параметры запуска</dt>
          <dd>
            <details>
              <summary className="cursor-pointer text-xs underline">показать JSON</summary>
              <pre className="mt-2 overflow-x-auto text-xs">
                {JSON.stringify(job.params_jsonb, null, 2)}
              </pre>
            </details>
          </dd>
        </div>
      </dl>
    </div>
  );
}
