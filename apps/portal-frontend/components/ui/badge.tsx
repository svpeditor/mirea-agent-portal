import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-[color:var(--color-accent)] text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent-hover)]',
        secondary:
          'border-transparent bg-[color:var(--color-bg-secondary)] text-[color:var(--color-text-primary)] hover:opacity-80',
        destructive:
          'border-transparent bg-[color:var(--color-error)] text-[color:var(--color-bg-primary)] hover:opacity-80',
        outline: 'text-[color:var(--color-text-primary)] border-[color:var(--color-border)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
