/**
 * Design tokens — экспортирует CSS-переменные из globals.css для рантайм-доступа из JS.
 * Используется для построения SVG-чартов, JS-вычисляемых стилей и т.п.
 *
 * Финал значений — после design-consultation.
 */
export const colors = {
  bgPrimary: 'var(--color-bg-primary)',
  bgSecondary: 'var(--color-bg-secondary)',
  textPrimary: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  accent: 'var(--color-accent)',
  accentHover: 'var(--color-accent-hover)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  info: 'var(--color-info)',
  border: 'var(--color-border)',
} as const;

export const fonts = {
  sans: 'var(--font-sans)',
  serif: 'var(--font-serif)',
  mono: 'var(--font-mono)',
} as const;
