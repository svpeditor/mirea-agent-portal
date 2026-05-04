import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

// Editorial button — square, sharp, no rounding. Inspired by academic action stamps.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-sans text-sm font-bold uppercase tracking-[0.08em] transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[color:var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--color-bg-primary)] disabled:pointer-events-none disabled:opacity-50 [border-radius:0]',
  {
    variants: {
      variant: {
        // Default — black ink stamp, hover crimson
        default:
          'border border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] text-[color:var(--color-bg-primary)] hover:border-[color:var(--color-accent)] hover:bg-[color:var(--color-accent)]',
        // Outline — paper with hairline border, hover invert
        outline:
          'border border-[color:var(--color-text-primary)] bg-transparent text-[color:var(--color-text-primary)] hover:bg-[color:var(--color-text-primary)] hover:text-[color:var(--color-bg-primary)]',
        // Ghost — minimal, hover paper-tint
        ghost:
          'text-[color:var(--color-text-primary)] hover:bg-[color:var(--color-bg-tertiary)] hover:text-[color:var(--color-accent)]',
        // Destructive — terracotta
        destructive:
          'border border-[color:var(--color-error)] bg-[color:var(--color-error)] text-[color:var(--color-bg-primary)] hover:bg-transparent hover:text-[color:var(--color-error)]',
        // Link — underline only
        link: 'normal-case tracking-normal text-[color:var(--color-accent)] underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2 text-xs',
        sm: 'h-8 px-3 text-[0.65rem]',
        lg: 'h-12 px-7 text-sm',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = 'Button';

export { buttonVariants };
