import type { APIRequestContext } from '@playwright/test';

const API_BASE = process.env.E2E_API_BASE ?? 'http://localhost:8000';

/**
 * Login через backend, возвращает строку cookie (`access_token=...; refresh_token=...`)
 * для дальнейших API request'ов в тестах.
 */
export async function loginViaApi(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const res = await request.post(`${API_BASE}/api/auth/login`, {
    data: { email, password },
  });
  if (!res.ok()) throw new Error(`Login failed: ${res.status()} ${await res.text()}`);
  // Set-Cookie header может быть массивом строк или одной строкой; нормализуем.
  const setCookie = res.headers()['set-cookie'] ?? '';
  // Из каждой строки берём только `name=value` (до первого `;`)
  const cookies = setCookie
    .split(/\r?\n/)
    .map((line) => line.split(';')[0].trim())
    .filter(Boolean)
    .join('; ');
  return cookies;
}

export const API_BASE_URL = API_BASE;
