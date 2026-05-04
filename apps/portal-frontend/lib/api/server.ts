import 'server-only';
import { cookies } from 'next/headers';
import { ApiError, type ApiErrorBody } from './types';

const API_BASE = process.env.API_BASE_URL ?? 'http://api:8000';

/**
 * Server-side fetch с cookies из request. Используется в RSC и Server Actions.
 *
 * @throws ApiError если status >= 400.
 */
export async function apiServer<T>(path: string, init?: RequestInit): Promise<T> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      Cookie: cookieHeader,
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
  });

  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      // ignore — body не JSON
    }
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) {
    return null as T;
  }
  return (await res.json()) as T;
}
