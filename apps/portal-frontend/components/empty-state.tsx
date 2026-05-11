import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[color:var(--color-border)] py-16 text-center">
      {icon && <div className="mb-4 text-4xl text-[color:var(--color-text-secondary)]">{icon}</div>}
      <h3 className="font-serif text-2xl">{title}</h3>
      {description && (
        <p className="mt-2 max-w-md text-[color:var(--color-text-secondary)]">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
