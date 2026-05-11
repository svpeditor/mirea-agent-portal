/**
 * Контракт событий, которые агент эмитирует в stdout как NDJSON.
 * Соответствует Python-SDK 1:1 (см. portal_sdk/events.py).
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface StartedEvent {
  type: 'started';
  ts: string;
}

export interface LogEvent {
  type: 'log';
  level: LogLevel;
  msg: string;
}

export interface ProgressEvent {
  type: 'progress';
  value: number; // 0..1
  label?: string | null;
}

export interface ItemDoneEvent {
  type: 'item_done';
  id: string;
  summary?: string | null;
  data?: Record<string, unknown> | null;
}

export interface ErrorEvent {
  type: 'error';
  id?: string | null;
  msg: string;
  retryable: boolean;
}

export interface Artifact {
  id: string;
  path: string;
}

export interface ResultEvent {
  type: 'result';
  artifacts: Artifact[];
}

export interface FailedEvent {
  type: 'failed';
  msg: string;
  details?: string | null;
}

export type AgentEvent =
  | StartedEvent
  | LogEvent
  | ProgressEvent
  | ItemDoneEvent
  | ErrorEvent
  | ResultEvent
  | FailedEvent;
