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
        const event = JSON.parse(e.data) as JobEventOut;
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
