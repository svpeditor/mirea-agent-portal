import Link from 'next/link';

export default function Forbidden() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-2xl flex-col justify-center px-8 py-20">
      <div className="ed-eyebrow mb-3 text-[color:var(--color-error)]">403 · ДОСТУП ЗАКРЫТ</div>
      <h1 className="ed-display text-5xl md:text-6xl">
        Только для<br />
        <span className="italic">редакции.</span>
      </h1>
      <p className="mt-6 max-w-md font-serif text-base text-[color:var(--color-text-secondary)]">
        Эта страница доступна только администраторам портала. Если думаешь, что это ошибка —
        свяжись с куратором НУГ.
      </p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/agents"
          className="ed-stamp border-2 border-[color:var(--color-text-primary)] bg-[color:var(--color-text-primary)] px-5 py-2.5 text-[color:var(--color-bg-primary)] no-underline hover:bg-[color:var(--color-accent)] hover:border-[color:var(--color-accent)]"
        >
          В каталог
        </Link>
        <Link
          href="/me"
          className="px-5 py-2.5 font-mono text-xs uppercase tracking-wider no-underline hover:text-[color:var(--color-accent)]"
        >
          Личный кабинет
        </Link>
      </div>
    </main>
  );
}
