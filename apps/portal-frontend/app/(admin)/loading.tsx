export default function Loading() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-6 sm:py-12">
      <div className="ed-anim-rise mb-10">
        <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
          РЕДАКЦИЯ ИЗВЕСТИЙ — загрузка…
        </div>
        <div className="h-20 w-72 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]" />
        <div className="mt-3 h-20 w-56 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-12 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]"
            style={{ animationDelay: `${i * 0.04}s` }}
          />
        ))}
      </div>
    </div>
  );
}
