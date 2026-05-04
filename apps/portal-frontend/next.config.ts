import type { NextConfig } from 'next';

const config: NextConfig = {
  output: 'standalone',
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    return [];
  },
};

export default config;
