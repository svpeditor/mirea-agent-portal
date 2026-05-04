/**
 * Helper для построения WebSocket URL из browser env.
 *
 * @example wsUrl('/api/jobs/123/stream', { since: 5 }) →
 *   'ws://localhost:8000/api/jobs/123/stream?since=5'
 */
export function wsUrl(path: string, params?: Record<string, string | number>): string {
  const base = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000';
  const url = new URL(`${base}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}
