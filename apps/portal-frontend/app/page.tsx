export default function HomePage() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-3xl">Портал НУГ — design tokens</h1>
      <p className="mt-4 text-[color:var(--color-text-secondary)]">
        Тёплый paper фон, сериф для заголовка, brick-red для акцентов.{' '}
        <a href="#">Это ссылка</a>.
      </p>
      <button className="mt-6 rounded-md bg-[color:var(--color-accent)] px-4 py-2 text-[color:var(--color-bg-primary)] hover:bg-[color:var(--color-accent-hover)]">
        Primary action
      </button>
    </main>
  );
}
