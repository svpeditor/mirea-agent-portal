import type { APIRequestContext } from '@playwright/test';
import { API_BASE_URL } from '../helpers/auth';

interface InviteCreateOut {
  id: string;
  token: string;
  email: string;
  expires_at: string;
  registration_url: string;
}

/**
 * Создаёт invite через admin API, возвращает токен.
 * Backend invite не имеет role — только email.
 */
export async function createInvite(
  request: APIRequestContext,
  adminCookie: string,
  email: string,
): Promise<string> {
  const res = await request.post(`${API_BASE_URL}/api/admin/invites`, {
    headers: { Cookie: adminCookie },
    data: { email },
  });
  if (!res.ok()) {
    throw new Error(`createInvite failed: ${res.status()} ${await res.text()}`);
  }
  const body = (await res.json()) as InviteCreateOut;
  return body.token;
}

/**
 * Регистрирует юзера по invite токену.
 */
export async function registerByInvite(
  request: APIRequestContext,
  token: string,
  email: string,
  password: string,
  displayName: string,
): Promise<void> {
  const res = await request.post(`${API_BASE_URL}/api/auth/register`, {
    data: { token, email, password, display_name: displayName },
  });
  if (!res.ok()) {
    throw new Error(`registerByInvite failed: ${res.status()} ${await res.text()}`);
  }
}
