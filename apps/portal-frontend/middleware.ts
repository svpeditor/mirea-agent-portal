import { NextResponse, type NextRequest } from 'next/server';
import { refreshTokens } from '@/lib/auth/refresh';

const PUBLIC_PATHS = ['/', '/login', '/register'];

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.includes(pathname)) return true;
  if (pathname.startsWith('/_next/')) return true;
  if (pathname.startsWith('/api/')) return true;  // proxy not used, но safety
  if (pathname.match(/\.(svg|png|jpg|ico|woff2)$/)) return true;
  return false;
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const accessToken = req.cookies.get('access_token')?.value;
  const refreshToken = req.cookies.get('refresh_token')?.value;

  // Если есть access_token — пропускаем (RSC сам провалит fetch если token истёк/невалиден)
  if (accessToken) {
    return NextResponse.next();
  }

  // Нет access_token. Если есть refresh_token — пробуем silent refresh.
  if (refreshToken) {
    const setCookies = await refreshTokens(refreshToken);
    if (setCookies) {
      const response = NextResponse.next();
      for (const cookie of setCookies) {
        response.headers.append('Set-Cookie', cookie);
      }
      return response;
    }
  }

  // Нет токенов или refresh не сработал — redirect на /login.
  const loginUrl = new URL('/login', req.url);
  loginUrl.searchParams.set('next', pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    /*
     * Все routes кроме:
     * - _next/static
     * - _next/image
     * - favicon.ico
     * - публичная статика (svg, png, etc.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|woff2?)$).*)',
  ],
};
