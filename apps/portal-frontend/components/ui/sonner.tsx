'use client';

import * as React from 'react';
import { CircleCheck, Info, LoaderCircle, OctagonX, TriangleAlert } from 'lucide-react';
import { Toaster as Sonner } from 'sonner';

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      icons={{
        success: <CircleCheck className="h-4 w-4" />,
        info: <Info className="h-4 w-4" />,
        warning: <TriangleAlert className="h-4 w-4" />,
        error: <OctagonX className="h-4 w-4" />,
        loading: <LoaderCircle className="h-4 w-4 animate-spin" />,
      }}
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-[color:var(--color-bg-primary)] group-[.toaster]:text-[color:var(--color-text-primary)] group-[.toaster]:border-[color:var(--color-border)] group-[.toaster]:shadow-lg',
          description: 'group-[.toast]:text-[color:var(--color-text-secondary)]',
          actionButton:
            'group-[.toast]:bg-[color:var(--color-accent)] group-[.toast]:text-[color:var(--color-bg-primary)]',
          cancelButton:
            'group-[.toast]:bg-[color:var(--color-bg-secondary)] group-[.toast]:text-[color:var(--color-text-secondary)]',
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
