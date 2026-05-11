/**
 * Design tokens — экспортирует CSS-переменные из globals.css для рантайм-доступа из JS.
 *
 * Применение: inline styles в JSX / SVG-чарты (для последних — вычислять через
 * getComputedStyle, эти строки сами по себе вне CSS не резолвятся).
 *
 * Палитра финализована в Wave 0.5 (Anthropic-школа + университетская editorial).
 */
export const colors = {
  bgPrimary: 'var(--color-bg-primary)',
  bgSecondary: 'var(--color-bg-secondary)',
  bgTertiary: 'var(--color-bg-tertiary)',
  textPrimary: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  textTertiary: 'var(--color-text-tertiary)',
  accent: 'var(--color-accent)',
  accentHover: 'var(--color-accent-hover)',
  accentSoft: 'var(--color-accent-soft)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  info: 'var(--color-info)',
  border: 'var(--color-border)',
  borderStrong: 'var(--color-border-strong)',
} as const;

export const fonts = {
  sans: 'var(--font-sans)',
  serif: 'var(--font-serif)',
  mono: 'var(--font-mono)',
} as const;
