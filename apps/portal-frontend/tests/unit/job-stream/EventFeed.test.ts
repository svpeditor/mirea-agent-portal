import { describe, it, expect } from 'vitest';
import { formatEventMessage } from '@/components/job-stream/EventFeed';
import type { JobEventOut } from '@/lib/api/types';

function evt(type: JobEventOut['type'], payload: Record<string, unknown>): JobEventOut {
  return { seq: 1, ts: '2026-05-11T00:00:00Z', type, payload };
}

describe('formatEventMessage', () => {
  it('log использует SDK-поле `msg`, не `message`', () => {
    expect(formatEventMessage(evt('log', { msg: 'hello world', level: 'info' })))
      .toBe('hello world');
  });

  it('failed использует SDK-поле `msg`', () => {
    expect(formatEventMessage(evt('failed', { msg: 'arxiv недоступен' })))
      .toBe('сбой · arxiv недоступен');
  });

  it('error использует SDK-поле `msg`', () => {
    expect(formatEventMessage(evt('error', { msg: 'timeout', retryable: true })))
      .toBe('timeout');
  });

  it('item_done использует поля `summary` и `id`, не `item_id`', () => {
    expect(
      formatEventMessage(
        evt('item_done', {
          id: 'arxiv:1706.03762',
          summary: 'Attention Is All You Need',
          data: { year: 2017 },
        }),
      ),
    ).toBe('готово · Attention Is All You Need');
  });

  it('item_done без summary показывает id', () => {
    expect(formatEventMessage(evt('item_done', { id: 'arxiv:1234' })))
      .toBe('готово · arxiv:1234');
  });

  it('started — статичная строка', () => {
    expect(formatEventMessage(evt('started', { ts: '...' }))).toBe('агент запущен');
  });

  it('result — статичная строка', () => {
    expect(formatEventMessage(evt('result', { artifacts: [] })))
      .toBe('задача завершена успешно');
  });
});
