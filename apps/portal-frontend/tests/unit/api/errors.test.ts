import { describe, it, expect } from 'vitest';
import { mapApiError, MESSAGES_RU } from '@/lib/api/errors';
import { ApiError } from '@/lib/api/types';

describe('mapApiError', () => {
  it('маппит known codes в RU-string', () => {
    const err = new ApiError(402, { error: { code: 'quota_exhausted', message: 'Quota exceeded' } });
    expect(mapApiError(err)).toBe(MESSAGES_RU.quota_exhausted);
  });

  it('возвращает backend message для unknown codes', () => {
    const err = new ApiError(400, { error: { code: 'unknown_code_xyz', message: 'Backend error message' } });
    expect(mapApiError(err)).toBe('Backend error message');
  });

  it('fallback на статус-код если нет body', () => {
    const err = new ApiError(500, null);
    expect(mapApiError(err)).toBe('Ошибка 500');
  });

  it('обрабатывает обычный Error', () => {
    expect(mapApiError(new Error('Network failed'))).toBe('Network failed');
  });

  it('обрабатывает unknown error type', () => {
    expect(mapApiError({ random: 'object' })).toBe('Что-то пошло не так. Попробуй ещё раз.');
  });

  it('покрывает все основные коды backend', () => {
    const required = [
      'invalid_credentials',
      'invite_expired',
      'quota_exhausted',
      'per_job_cap_exceeded',
      'invalid_ephemeral_token',
      'model_not_in_whitelist',
      'not_implemented',
      'openrouter_upstream_error',
      'job_not_found',
      'agent_not_ready',
    ];
    for (const code of required) {
      expect(MESSAGES_RU[code]).toBeDefined();
      expect(MESSAGES_RU[code]).toMatch(/[А-Яа-я]/);  // RU text
    }
  });
});
