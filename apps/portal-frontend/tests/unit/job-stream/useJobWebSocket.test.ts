import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useJobWebSocket } from '@/components/job-stream/useJobWebSocket';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(_data: string) {}
  close() {
    this.readyState = 3;
    this.onclose?.(new CloseEvent('close'));
  }

  simulateOpen() {
    this.readyState = 1;
    this.onopen?.(new Event('open'));
  }
  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
  simulateClose() {
    this.readyState = 3;
    this.onclose?.(new CloseEvent('close'));
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useJobWebSocket', () => {
  it('подключается с правильным URL включая since', () => {
    renderHook(() =>
      useJobWebSocket({
        jobId: 'abc',
        initialEvents: [{ seq: 5 } as never],
        onTerminal: vi.fn(),
      }),
    );
    expect(MockWebSocket.instances[0]?.url).toContain('/api/jobs/abc/stream');
    expect(MockWebSocket.instances[0]?.url).toContain('since=5');
  });

  it('накапливает events из WebSocket', () => {
    const { result } = renderHook(() =>
      useJobWebSocket({ jobId: 'abc', initialEvents: [], onTerminal: vi.fn() }),
    );
    const ws = MockWebSocket.instances[0]!;
    act(() => { ws.simulateOpen(); });
    act(() => { ws.simulateMessage({ seq: 1, type: 'started', ts: '2026-05-03T00:00:00Z', payload: {} }); });
    act(() => { ws.simulateMessage({ seq: 2, type: 'progress', ts: '2026-05-03T00:00:01Z', payload: { value: 0.5 } }); });
    expect(result.current.events).toHaveLength(2);
  });

  it('вызывает onTerminal при result/failed/etc', () => {
    const onTerminal = vi.fn();
    renderHook(() =>
      useJobWebSocket({ jobId: 'abc', initialEvents: [], onTerminal }),
    );
    const ws = MockWebSocket.instances[0]!;
    act(() => { ws.simulateOpen(); });
    act(() => { ws.simulateMessage({ seq: 1, type: 'result', ts: 'x', payload: {} }); });
    expect(onTerminal).toHaveBeenCalledWith('result');
  });

  it('переподключается на close с обновлённым since', () => {
    vi.useFakeTimers();
    renderHook(() =>
      useJobWebSocket({
        jobId: 'abc',
        initialEvents: [{ seq: 3 } as never],
        onTerminal: vi.fn(),
      }),
    );
    const ws1 = MockWebSocket.instances[0]!;
    act(() => { ws1.simulateOpen(); });
    act(() => { ws1.simulateMessage({ seq: 4, type: 'log', ts: 'x', payload: {} }); });
    act(() => { ws1.simulateClose(); });
    act(() => { vi.advanceTimersByTime(1000); });
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1]?.url).toContain('since=4');
    vi.useRealTimers();
  });
});
