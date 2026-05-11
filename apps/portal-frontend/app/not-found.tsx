import Link from 'next/link';
import type { Route } from 'next';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <h1 className="font-serif text-6xl">404</h1>
      <p className="mt-4 text-[color:var(--color-text-secondary)]">Страница не найдена.</p>
      <Button asChild className="mt-6">
        <Link href={'/' as Route} className="no-underline">
          На главную
        </Link>
      </Button>
    </div>
  );
}
