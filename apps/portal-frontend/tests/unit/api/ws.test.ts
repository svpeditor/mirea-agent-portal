import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { wsUrl } from '@/lib/api/ws';

describe('wsUrl', () => {
  const original = process.env.NEXT_PUBLIC_WS_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
    if (typeof document !== 'undefined') {
      document.cookie.split(';').forEach((c) => {
        const eq = c.indexOf('=');
        const name = eq > -1 ? c.substring(0, eq).trim() : c.trim();
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
      });
    }
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

  it('фильтрует undefined params (не пишет since=undefined)', () => {
    const url = wsUrl('/api/jobs/abc/stream', {
      since: undefined as unknown as number,
    });
    expect(url).toBe('ws://localhost:8000/api/jobs/abc/stream');
  });

  it('добавляет ?token= из ws_token cookie если есть', () => {
    document.cookie = 'ws_token=abc123';
    const url = wsUrl('/api/jobs/x/stream', { since: 0 });
    expect(url).toContain('token=abc123');
    expect(url).toContain('since=0');
  });

  it('не добавляет ?token= если ws_token cookie пуст', () => {
    const url = wsUrl('/api/jobs/x/stream', { since: 0 });
    expect(url).not.toContain('token=');
  });
});
