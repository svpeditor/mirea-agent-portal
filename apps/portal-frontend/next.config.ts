import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  // authInterrupts — нужен для forbidden() / unauthorized() из next/navigation.
  experimental: {
    authInterrupts: true,
  },
  // typedRoutes выключен — Turbopack (default в Next 15.1 dev) пока не поддерживает.
  // `as Route` касты в коде остаются, просто становятся no-op type-widening.
  // Прокси /api/* → backend. В docker compose API_BASE_URL=http://api:8000 (внутренний DNS).
  // Локально (npm run dev) — fallback на http://localhost:8000.
  async rewrites() {
    const apiBase = process.env.API_BASE_URL ?? 'http://localhost:8000';
    return [{ source: '/api/:path*', destination: `${apiBase}/api/:path*` }];
  },
};

export default config;
