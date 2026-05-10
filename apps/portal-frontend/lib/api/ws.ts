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
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  // Cross-port WS handshake не подхватывает httpOnly cookie. Backend кладёт дубль
  // в non-httpOnly `ws_token` — фронт читает и передаёт явно.
  if (typeof document !== 'undefined') {
    const m = document.cookie.match(/(?:^|;\s*)ws_token=([^;]+)/);
    if (m && m[1]) url.searchParams.set('token', decodeURIComponent(m[1]));
  }
  return url.toString();
}
