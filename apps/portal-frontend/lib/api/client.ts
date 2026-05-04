'use client';
import { ApiError, type ApiErrorBody } from './types';

/**
 * Client-side fetch — cookies автоматически отправляются browser'ом.
 *
 * @throws ApiError если status >= 400.
 */
export async function apiClient<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      ...init?.headers,
      ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    },
  });

  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) {
    return null as T;
  }
  return (await res.json()) as T;
}
