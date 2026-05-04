import type { JobDetailOut } from '@/lib/api/types';
import { formatDate } from '@/lib/format';

export function JobMeta({ job }: { job: JobDetailOut }) {
  return (
    <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-4">
      <h3 className="mb-3 font-serif text-lg">Параметры</h3>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-[color:var(--color-text-secondary)]">Создано</dt>
          <dd>{formatDate(job.created_at)}</dd>
        </div>
        {job.started_at && (
          <div>
            <dt className="text-[color:var(--color-text-secondary)]">Запущено</dt>
            <dd>{formatDate(job.started_at)}</dd>
          </div>
        )}
        {job.finished_at && (
          <div>
            <dt className="text-[color:var(--color-text-secondary)]">Завершено</dt>
            <dd>{formatDate(job.finished_at)}</dd>
          </div>
        )}
        <div>
          <dt className="text-[color:var(--color-text-secondary)]">Параметры запуска</dt>
          <dd>
            <details>
              <summary className="cursor-pointer text-xs underline">показать JSON</summary>
              <pre className="mt-2 overflow-x-auto text-xs">
                {JSON.stringify(job.params, null, 2)}
              </pre>
            </details>
          </dd>
        </div>
        {job.output_summary && (
          <div>
            <dt className="text-[color:var(--color-text-secondary)]">Сводка результата</dt>
            <dd>
              <details>
                <summary className="cursor-pointer text-xs underline">показать JSON</summary>
                <pre className="mt-2 overflow-x-auto text-xs">
                  {JSON.stringify(job.output_summary, null, 2)}
                </pre>
              </details>
            </dd>
          </div>
        )}
        {job.error_msg && (
          <div>
            <dt className="text-[color:var(--color-text-secondary)]">Ошибка</dt>
            <dd className="text-[color:var(--color-error)]">{job.error_msg}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
