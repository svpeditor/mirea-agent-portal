'use client';
import { formatCurrency } from '@/lib/format';

interface Bar {
  label: string;
  value: number;
  rawString: string;
}

export function UsageBarChart({ bars }: { bars: Bar[] }) {
  if (bars.length === 0) {
    return (
      <p className="text-sm text-[color:var(--color-text-secondary)]">Нет данных за период.</p>
    );
  }
  const max = Math.max(...bars.map((b) => b.value), 0.000001);

  return (
    <div className="space-y-2">
      {bars.slice(0, 10).map((bar) => {
        const pct = (bar.value / max) * 100;
        return (
          <div key={bar.label} className="text-sm">
            <div className="mb-1 flex justify-between gap-2">
              <span className="truncate">{bar.label}</span>
              <span className="font-mono text-xs">{formatCurrency(bar.rawString)}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-[color:var(--color-bg-secondary)]">
              <div
                className="h-full bg-[color:var(--color-accent)] transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
