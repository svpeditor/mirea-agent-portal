import { describe, it, expect } from 'vitest';
import { formatDuration, formatCurrency } from '@/lib/format';

describe('formatDuration', () => {
  it('секунды', () => {
    expect(formatDuration('2026-01-01T00:00:00Z', '2026-01-01T00:00:05Z')).toBe('5с');
  });

  it('минуты и секунды', () => {
    expect(formatDuration('2026-01-01T00:00:00Z', '2026-01-01T00:01:30Z')).toBe('1м 30с');
  });

  it('часы и минуты', () => {
    expect(formatDuration('2026-01-01T00:00:00Z', '2026-01-01T01:30:00Z')).toBe('1ч 30м');
  });

  it('начало без конца — длительность от старта до now', () => {
    const now = new Date();
    const past = new Date(now.getTime() - 5000).toISOString();
    const result = formatDuration(past, null);
    expect(result).toMatch(/^\d+с$/);
  });
});

describe('formatCurrency', () => {
  it('zero → прочерк', () => {
    expect(formatCurrency('0')).toBe('—');
    expect(formatCurrency('0.000000')).toBe('—');
  });

  it('< 0.01 → <$0.01', () => {
    expect(formatCurrency('0.005')).toBe('<$0.01');
  });

  it('обычные значения с 2 знаками', () => {
    expect(formatCurrency('1.234')).toBe('$1.23');
    expect(formatCurrency('10.5')).toBe('$10.50');
  });

  it('невалидное → прочерк', () => {
    expect(formatCurrency('foo')).toBe('—');
  });
});
