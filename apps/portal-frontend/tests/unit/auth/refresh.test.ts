import { describe, it, expect, vi, beforeEach } from 'vitest';
import { refreshTokens } from '@/lib/auth/refresh';

describe('refreshTokens', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('возвращает Set-Cookie headers при успешном refresh', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: {
        getSetCookie: () => [
          'access_token=new-access; HttpOnly',
          'refresh_token=new-refresh; HttpOnly',
        ],
      },
    });

    const result = await refreshTokens('old-refresh-token');
    expect(result).toEqual([
      'access_token=new-access; HttpOnly',
      'refresh_token=new-refresh; HttpOnly',
    ]);
  });

  it('возвращает null при HTTP error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: { getSetCookie: () => [] },
    });

    const result = await refreshTokens('expired-refresh');
    expect(result).toBeNull();
  });

  it('возвращает null при network error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network down'));

    const result = await refreshTokens('any-token');
    expect(result).toBeNull();
  });

  it('отправляет refresh_token в Cookie header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { getSetCookie: () => ['access_token=x'] },
    });
    global.fetch = fetchMock;

    await refreshTokens('my-refresh-123');

    const call = fetchMock.mock.calls[0];
    expect(call?.[1]?.headers).toMatchObject({
      Cookie: 'refresh_token=my-refresh-123',
    });
  });
});
