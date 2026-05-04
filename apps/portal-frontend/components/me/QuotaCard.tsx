import type { UserQuotaOut } from '@/lib/api/types';
import { formatDate, formatCurrency } from '@/lib/format';
import { Progress } from '@/components/ui/progress';

export function QuotaCard({ quota }: { quota: UserQuotaOut }) {
  const used = parseFloat(quota.period_used_usd) || 0;
  const limit = parseFloat(quota.monthly_limit_usd) || 0;
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;

  return (
    <div className="space-y-6 rounded-lg border border-[color:var(--color-border)] p-6">
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span>Месячный лимит</span>
          <span className="font-mono">
            {formatCurrency(quota.period_used_usd)} / {formatCurrency(quota.monthly_limit_usd)}
          </span>
        </div>
        <Progress value={pct} className="h-2" />
        <p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">
          Период начался {formatDate(quota.period_starts_at)} (МСК). Сбросится 1-го числа следующего месяца.
        </p>
      </div>

      <div className="border-t border-[color:var(--color-border)] pt-4">
        <div className="flex justify-between text-sm">
          <span>Лимит на одну задачу</span>
          <span className="font-mono">{formatCurrency(quota.per_job_cap_usd)}</span>
        </div>
        <p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">
          На каждой задаче отдельно может быть потрачено не больше этой суммы.
        </p>
      </div>

      <div className="rounded-md bg-[color:var(--color-bg-secondary)] p-4 text-sm">
        <strong>Что такое квота?</strong>
        <p className="mt-1 text-[color:var(--color-text-secondary)]">
          Когда агент использует LLM (через OpenRouter), портал считает стоимость.
          Когда исчерпаешь месячный лимит - новые задачи временно недоступны до сброса.
          Если нужно больше - попроси админа НУГ повысить лимит.
        </p>
      </div>
    </div>
  );
}
