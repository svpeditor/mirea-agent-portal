'use client';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/drawer';
import type { ReactNode } from 'react';

interface Props {
  paramName: string;         // ?drawer=user-123 -> paramName="drawer"
  paramValue: string | null; // currently open drawer value (null = closed)
  title: string;
  children: ReactNode;
}

export function DrawerSheet({ paramName, paramValue, title, children }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const open = !!paramValue;

  function close() {
    const params = new URLSearchParams(searchParams);
    params.delete(paramName);
    router.replace(`?${params.toString()}` as never);
  }

  return (
    <Sheet open={open} onOpenChange={(o) => !o && close()}>
      <SheetContent className="w-full max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <div className="mt-6">{children}</div>
      </SheetContent>
    </Sheet>
  );
}
