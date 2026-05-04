import 'server-only';

const API_BASE = process.env.API_BASE_URL ?? 'http://api:8000';

/**
 * Server-side refresh: отправляет refresh_token cookie на /api/auth/refresh,
 * возвращает Set-Cookie headers (для проброса в response).
 *
 * @returns массив Set-Cookie строк или null если refresh не сработал.
 */
export async function refreshTokens(refreshToken: string): Promise<string[] | null> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        Cookie: `refresh_token=${refreshToken}`,
      },
      // no-store: refresh response must never be cached — каждый запрос даёт новые tokens.
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const setCookieHeaders = res.headers.getSetCookie?.() ?? [];
    return setCookieHeaders.length > 0 ? setCookieHeaders : null;
  } catch {
    return null;
  }
}
