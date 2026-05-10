'use client';
import { useEffect, useRef, useState } from 'react';
import type { JobEventOut } from '@/lib/api/types';
import { wsUrl } from '@/lib/api/ws';

const TERMINAL_TYPES = new Set(['result', 'failed', 'cancelled', 'timed_out', 'error']);

interface Props {
  jobId: string;
  initialEvents: JobEventOut[];
  onTerminal: (type: string) => void;
}

interface Result {
  events: JobEventOut[];
  connected: boolean;
}

export function useJobWebSocket({ jobId, initialEvents, onTerminal }: Props): Result {
  const [events, setEvents] = useState<JobEventOut[]>(initialEvents);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSeqRef = useRef<number>(initialEvents[initialEvents.length - 1]?.seq ?? 0);
  const isTerminalRef = useRef(false);
  const onTerminalRef = useRef(onTerminal);

  // Keep latest callback in ref so connect() closure stays fresh without re-running effect
  useEffect(() => {
    onTerminalRef.current = onTerminal;
  }, [onTerminal]);

  useEffect(() => {
    function connect() {
      if (isTerminalRef.current) return;
      const url = wsUrl(`/api/jobs/${jobId}/stream`, { since: lastSeqRef.current });
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data) as
          | JobEventOut
          | { type: 'resync'; events: JobEventOut[] };

        // Resync — пришёл список пропущенных событий, не отдельное событие.
        if ((msg as { type?: string }).type === 'resync') {
          const incoming = ((msg as { events?: JobEventOut[] }).events ?? []).filter(
            (x) => typeof x.seq === 'number' && typeof x.ts === 'string',
          );
          if (incoming.length === 0) return;
          setEvents((prev) => {
            const known = new Set(prev.map((x) => x.seq));
            const fresh = incoming.filter((x) => !known.has(x.seq));
            return [...prev, ...fresh].sort((a, b) => a.seq - b.seq);
          });
          const lastSeq = Math.max(...incoming.map((x) => x.seq));
          if (lastSeq > lastSeqRef.current) lastSeqRef.current = lastSeq;
          const terminal = incoming.find((x) => TERMINAL_TYPES.has(x.type));
          if (terminal) {
            isTerminalRef.current = true;
            onTerminalRef.current(terminal.type);
            ws.close();
          }
          return;
        }

        const event = msg as JobEventOut;
        if (typeof event.seq !== 'number' || typeof event.ts !== 'string') return;
        setEvents((prev) => [...prev, event]);
        lastSeqRef.current = event.seq;
        if (TERMINAL_TYPES.has(event.type)) {
          isTerminalRef.current = true;
          onTerminalRef.current(event.type);
          ws.close();
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!isTerminalRef.current) {
          reconnectTimerRef.current = setTimeout(connect, 1000);
        }
      };
      ws.onerror = () => {
        // noop — reconnect is handled via onclose
      };
    }

    connect();

    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
    // Intentionally narrow deps: initialEvents and onTerminal are captured via refs above;
    // only jobId change should restart the WebSocket connection.
  }, [jobId]);

  return { events, connected };
}
