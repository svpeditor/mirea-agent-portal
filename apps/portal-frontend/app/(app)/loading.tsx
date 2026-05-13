export default function Loading() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-8 py-6 sm:py-12">
      <div className="ed-anim-rise mb-12 grid gap-8 md:grid-cols-[2fr_1fr]">
        <div>
          <div className="ed-eyebrow mb-3 text-[color:var(--color-accent)]">
            ЗАГРУЗКА…
          </div>
          <div className="h-20 w-80 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]" />
          <div className="mt-3 h-20 w-60 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]" />
        </div>
        <div className="hidden md:flex md:justify-end">
          <div className="h-8 w-32 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]" />
        </div>
      </div>

      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-14 animate-pulse rounded-none bg-[color:var(--color-bg-tertiary)]"
            style={{ animationDelay: `${i * 0.05}s` }}
          />
        ))}
      </div>
    </div>
  );
}
