import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  // typedRoutes выключен — Turbopack (default в Next 15.1 dev) пока не поддерживает.
  // `as Route` касты в коде остаются, просто становятся no-op type-widening.
  async rewrites() {
    return process.env.NODE_ENV === 'development'
      ? [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }]
      : [];
  },
};

export default config;
