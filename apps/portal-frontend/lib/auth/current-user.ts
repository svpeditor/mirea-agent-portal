import 'server-only';
import { cache } from 'react';
import { forbidden } from 'next/navigation';
import { apiServer } from '@/lib/api/server';
import { ApiError, type UserMeOut } from '@/lib/api/types';

/**
 * Возвращает текущего юзера из /api/me. Кешируется per-request через React.cache().
 *
 * @returns UserMeOut если залогинен, null если 401.
 */
export const getCurrentUser = cache(async (): Promise<UserMeOut | null> => {
  try {
    return await apiServer<UserMeOut>('/api/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return null;
    }
    throw err;
  }
});

/**
 * Гарантирует что юзер залогинен; в RSC бросает на null (Next.js redirect должен
 * сработать через middleware ещё раньше; это safety net).
 */
export async function requireUser(): Promise<UserMeOut> {
  const user = await getCurrentUser();
  if (user === null) {
    throw new Error('Not authenticated — middleware should have redirected');
  }
  return user;
}

/**
 * Гарантирует admin role. Использует Next.js 15.1+ `forbidden()` — он
 * рендерит app/forbidden.tsx (HTTP 403), а не 500 error page.
 */
export async function requireAdmin(): Promise<UserMeOut> {
  const user = await requireUser();
  if (user.role !== 'admin') {
    forbidden();
  }
  return user;
}
