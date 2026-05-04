import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { wsUrl } from '@/lib/api/ws';

describe('wsUrl', () => {
  const original = process.env.NEXT_PUBLIC_WS_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
  });

  afterEach(() => {
    if (original === undefined) delete process.env.NEXT_PUBLIC_WS_URL;
    else process.env.NEXT_PUBLIC_WS_URL = original;
  });

  it('строит URL без query при params=undefined', () => {
    expect(wsUrl('/api/jobs/abc/stream')).toBe('ws://localhost:8000/api/jobs/abc/stream');
  });

  it('добавляет string params', () => {
    expect(wsUrl('/x', { foo: 'bar' })).toBe('ws://localhost:8000/x?foo=bar');
  });

  it('коэрсит number params в string', () => {
    expect(wsUrl('/api/jobs/123/stream', { since: 5 })).toBe(
      'ws://localhost:8000/api/jobs/123/stream?since=5',
    );
  });
});
