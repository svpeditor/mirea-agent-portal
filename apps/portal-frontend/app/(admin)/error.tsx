'use client';
import { Button } from '@/components/ui/button';
import { mapApiError } from '@/lib/api/errors';

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="font-serif text-3xl">Что-то пошло не так</h1>
      <p className="mt-4 text-[color:var(--color-text-secondary)]">{mapApiError(error)}</p>
      <Button className="mt-6" onClick={reset}>
        Попробовать ещё раз
      </Button>
    </div>
  );
}
