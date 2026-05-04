import { ApiError } from './types';

/**
 * Маппинг backend error.code → user-friendly RU-string.
 *
 * Используется в toast'ах и error boundaries.
 */
export const MESSAGES_RU: Record<string, string> = {
  // Auth
  invalid_credentials: 'Неверный email или пароль.',
  user_not_found: 'Пользователь не найден.',
  invite_expired: 'Приглашение истекло или уже использовано.',
  invite_invalid: 'Ссылка-приглашение неверна.',
  invite_used: 'Приглашение уже использовано. Свяжись с админом за новым.',
  email_already_exists: 'Email уже зарегистрирован.',
  password_too_short: 'Пароль слишком короткий (минимум 12 символов).',
  password_too_weak: 'Пароль слишком простой. Добавь цифры, буквы разного регистра.',

  // Quotas / LLM proxy
  quota_exhausted: 'Месячная квота исчерпана. Обновится 1-го числа.',
  per_job_cap_exceeded: 'На этой задаче исчерпан лимит стоимости.',
  invalid_ephemeral_token: 'Сессия LLM истекла. Перезапусти задачу.',
  model_not_in_whitelist: 'Эта модель не разрешена для агента.',
  not_implemented: 'Эта функция пока не поддерживается.',
  openrouter_upstream_error: 'OpenRouter временно недоступен. Попробуй позже.',
  openrouter_timeout: 'OpenRouter не ответил вовремя. Попробуй позже.',

  // Jobs / Agents
  job_not_found: 'Задача не найдена.',
  agent_not_ready: 'Агент ещё собирается. Попробуй через минуту.',
  agent_not_found: 'Агент не найден.',
  agent_disabled: 'Агент временно отключён.',
  job_already_terminal: 'Задача уже завершена.',
  cannot_cancel: 'Эту задачу нельзя отменить (уже завершена).',
  invalid_input: 'Неверные параметры запуска.',
  file_too_large: 'Файл слишком большой.',

  // Admin
  forbidden: 'Только админ может это сделать.',
  user_quota_not_found: 'Квота пользователя не найдена.',
  tab_in_use: 'У этого таба есть агенты. Удали их сначала.',
};

/**
 * Маппит ApiError в RU-string. Fallback на error.message → дефолт.
 */
export function mapApiError(err: unknown): string {
  if (err instanceof ApiError) {
    const code = err.body?.error?.code;
    if (code && MESSAGES_RU[code]) {
      return MESSAGES_RU[code];
    }
    return err.body?.error?.message ?? `Ошибка ${err.status}`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return 'Что-то пошло не так. Попробуй ещё раз.';
}
