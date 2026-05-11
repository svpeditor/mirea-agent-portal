/**
 * Agent — обёртка над контрактом портала (TypeScript).
 *
 * Читает $PARAMS_FILE, $INPUT_DIR, $OUTPUT_DIR из env при инициализации.
 * Автоматически отправляет событие `started`. События — NDJSON в stdout.
 */
import { readFileSync, existsSync, statSync } from 'node:fs';
import * as path from 'node:path';
import type {
  AgentEvent,
  Artifact,
  LogLevel,
  StartedEvent,
} from './events.js';

const FINISHED_MSG = 'Агент уже завершён (result/failed уже отправлен).';

/** Куда писать NDJSON. По умолчанию process.stdout. Тестам удобно подменять. */
export interface AgentWriter {
  write(chunk: string): boolean;
}

export interface AgentOptions {
  writer?: AgentWriter;
}

export class Agent {
  readonly params: Record<string, unknown>;
  readonly outputDir: string;

  private readonly _inputDir: string;
  private readonly _writer: AgentWriter;
  private _finished = false;

  constructor(opts: AgentOptions = {}) {
    this._writer = opts.writer ?? process.stdout;
    const paramsFile = process.env.PARAMS_FILE;
    const inputDir = process.env.INPUT_DIR;
    const outputDir = process.env.OUTPUT_DIR;

    if (!paramsFile || !inputDir || !outputDir) {
      const missing = [
        !paramsFile && 'PARAMS_FILE',
        !inputDir && 'INPUT_DIR',
        !outputDir && 'OUTPUT_DIR',
      ]
        .filter(Boolean)
        .join(', ');
      throw new Error(
        `Обязательные env-переменные не установлены: ${missing}. ` +
          'Для локального запуска используй CLI portal-sdk-run-local (Python) или эмулируй env.',
      );
    }
    if (!existsSync(paramsFile)) {
      throw new Error(`PARAMS_FILE не найден: ${paramsFile}`);
    }

    this._inputDir = inputDir;
    this.outputDir = outputDir;

    const raw = JSON.parse(readFileSync(paramsFile, 'utf-8')) as unknown;
    if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
      throw new TypeError(
        `PARAMS_FILE должен содержать JSON-объект, получен ${typeof raw}.`,
      );
    }
    this.params = raw as Record<string, unknown>;

    this._emit({
      type: 'started',
      ts: new Date().toISOString(),
    } satisfies StartedEvent);
  }

  /**
   * Путь к папке с пользовательскими файлами для input_id (из manifest.files).
   * Бросает если папка не найдена (объявленный files-input не пришёл).
   */
  inputDir(inputId: string): string {
    const p = path.join(this._inputDir, inputId);
    if (!existsSync(p)) {
      throw new Error(
        `Input '${inputId}' не найден в ${this._inputDir}. ` +
          `Проверь что в manifest.yaml есть files.${inputId}.`,
      );
    }
    return p;
  }

  /** Числовой прогресс 0..1 + опциональная подпись. */
  progress(value: number, label?: string): void {
    this._guard();
    const clamped = Math.max(0, Math.min(1, value));
    this._emit({ type: 'progress', value: clamped, label: label ?? null });
  }

  /** Сообщение в общую ленту задачи. */
  log(level: LogLevel, msg: string): void {
    this._guard();
    this._emit({ type: 'log', level, msg });
  }

  /** Завершение одного элемента в серии (например, одной работы из 46). */
  itemDone(
    id: string,
    summary?: string,
    data?: Record<string, unknown>,
  ): void {
    this._guard();
    this._emit({
      type: 'item_done',
      id,
      summary: summary ?? null,
      data: data ?? null,
    });
  }

  /** Нефатальная ошибка по элементу. Агент продолжает. */
  error(msg: string, itemId?: string, retryable = true): void {
    this._guard();
    this._emit({ type: 'error', id: itemId ?? null, msg, retryable });
  }

  /**
   * Финальное событие успеха. Artifacts — список `{id, path}` где
   * path относителен outputDir; SDK проверит что файлы существуют.
   */
  result(artifacts: Artifact[]): void {
    this._guard();
    if (artifacts.length === 0) {
      throw new Error(
        'result() вызван с пустым списком артефактов. ' +
          'Добавь хотя бы один файл или используй failed() если нечего вернуть.',
      );
    }
    for (const a of artifacts) {
      if (path.isAbsolute(a.path)) {
        throw new Error(
          `Путь артефакта '${a.id}' должен быть относительным к outputDir, ` +
            `получен абсолютный: ${a.path}.`,
        );
      }
      const full = path.resolve(this.outputDir, a.path);
      const root = path.resolve(this.outputDir);
      if (!full.startsWith(root + path.sep) && full !== root) {
        throw new Error(
          `Путь артефакта '${a.id}' выходит за пределы outputDir: ${a.path}.`,
        );
      }
      if (!existsSync(full) || !statSync(full).isFile()) {
        throw new Error(
          `Артефакт '${a.id}' не найден: ${full}. ` +
            'Перед result() надо записать файл в outputDir.',
        );
      }
    }
    this._emit({ type: 'result', artifacts });
    this._finished = true;
  }

  /** Финальное событие неуспеха. */
  failed(msg: string, details?: string): void {
    this._guard();
    this._emit({ type: 'failed', msg, details: details ?? null });
    this._finished = true;
  }

  private _guard(): void {
    if (this._finished) throw new Error(FINISHED_MSG);
  }

  private _emit(event: AgentEvent): void {
    const clean = JSON.stringify(event, (_, v) => (v === null ? null : v));
    this._writer.write(clean + '\n');
  }
}
