import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DisplayNameEditor } from '@/components/me/DisplayNameEditor';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

const apiClientMock = vi.fn();
vi.mock('@/lib/api/client', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}));

const toastError = vi.fn();
const toastSuccess = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...a: unknown[]) => toastError(...a),
    success: (...a: unknown[]) => toastSuccess(...a),
  },
}));

beforeEach(() => {
  apiClientMock.mockReset();
  toastError.mockReset();
  toastSuccess.mockReset();
});

describe('DisplayNameEditor', () => {
  it('показывает текущее имя и кнопку редактирования', () => {
    render(<DisplayNameEditor current="Иван" />);
    expect(screen.getByText('Иван')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Изменить имя/i })).toBeTruthy();
  });

  it('клик по карандашу открывает input', () => {
    render(<DisplayNameEditor current="Иван" />);
    fireEvent.click(screen.getByRole('button', { name: /Изменить имя/i }));
    const input = screen.getByDisplayValue('Иван') as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.tagName).toBe('INPUT');
  });

  it('Escape отменяет редактирование', () => {
    render(<DisplayNameEditor current="Иван" />);
    fireEvent.click(screen.getByRole('button', { name: /Изменить имя/i }));
    const input = screen.getByDisplayValue('Иван');
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(screen.queryByDisplayValue('Иван')).toBeNull();
    expect(apiClientMock).not.toHaveBeenCalled();
  });

  it('пустое имя — toast.error, апи не вызывается', async () => {
    render(<DisplayNameEditor current="Иван" />);
    fireEvent.click(screen.getByRole('button', { name: /Изменить имя/i }));
    const input = screen.getByDisplayValue('Иван');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByRole('button', { name: /Сохранить/i }));
    await waitFor(() => expect(toastError).toHaveBeenCalled());
    expect(apiClientMock).not.toHaveBeenCalled();
  });

  it('Enter сохраняет: PATCH /api/me + toast.success', async () => {
    apiClientMock.mockResolvedValueOnce({});
    render(<DisplayNameEditor current="Иван" />);
    fireEvent.click(screen.getByRole('button', { name: /Изменить имя/i }));
    const input = screen.getByDisplayValue('Иван');
    fireEvent.change(input, { target: { value: 'Даня' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(apiClientMock).toHaveBeenCalled());
    expect(apiClientMock.mock.calls[0][0]).toBe('/api/me');
    expect(apiClientMock.mock.calls[0][1].method).toBe('PATCH');
    expect(apiClientMock.mock.calls[0][1].body).toContain('"display_name":"Даня"');
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled());
  });

  it('если имя не изменилось — выходит из edit-режима без вызова API', () => {
    render(<DisplayNameEditor current="Иван" />);
    fireEvent.click(screen.getByRole('button', { name: /Изменить имя/i }));
    const input = screen.getByDisplayValue('Иван');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(apiClientMock).not.toHaveBeenCalled();
  });
});
