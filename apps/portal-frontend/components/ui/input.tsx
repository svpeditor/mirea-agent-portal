import * as React from 'react';
import { cn } from '@/lib/utils';

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Editorial input — no rounding, hairline-bottom focus, paper background.
          'flex h-11 w-full border-0 border-b border-[color:var(--color-text-primary)] bg-transparent px-1 py-2 font-sans text-base text-[color:var(--color-text-primary)] file:border-0 file:bg-transparent file:font-mono file:text-xs file:font-medium placeholder:font-serif placeholder:italic placeholder:text-[color:var(--color-text-tertiary)] focus-visible:border-b-2 focus-visible:border-[color:var(--color-accent)] focus-visible:outline-none focus-visible:pb-[7px] disabled:cursor-not-allowed disabled:opacity-60 md:text-sm [border-radius:0]',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';

export { Input };
