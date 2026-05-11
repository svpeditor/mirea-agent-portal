import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AvatarUploader } from '@/components/me/AvatarUploader';

// next/navigation мок — компонент дёргает useRouter().refresh()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

// apiClient мок — без сети
const apiClientMock = vi.fn();
vi.mock('@/lib/api/client', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}));

// sonner toast мок
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

describe('AvatarUploader', () => {
  it('без аватара показывает инициалы и кнопку «Загрузить»', () => {
    render(<AvatarUploader hasAvatar={false} avatarVersion={null} initials="ДА" />);
    expect(screen.getByText('ДА')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Загрузить/i })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Удалить/i })).toBeNull();
  });

  it('с аватаром показывает <img> с cache-buster и кнопку «Заменить»', () => {
    render(<AvatarUploader hasAvatar avatarVersion="abc12345" initials="ДА" />);
    const img = screen.getByAltText('Аватар') as HTMLImageElement;
    expect(img.src).toContain('/api/me/avatar?v=');
    expect(img.src).toContain('abc12345');
    expect(screen.getByRole('button', { name: /Заменить/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Удалить/i })).toBeTruthy();
  });

  it('отказывает не-image content-type', async () => {
    const { container } = render(
      <AvatarUploader hasAvatar={false} avatarVersion={null} initials="ДА" />,
    );
    const input = container.querySelector('input[type=file]') as HTMLInputElement;
    const file = new File(['x'], 'evil.exe', { type: 'application/x-msdownload' });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(toastError).toHaveBeenCalled());
    expect(toastError.mock.calls[0][0]).toMatch(/PNG, JPEG или WebP/i);
    expect(apiClientMock).not.toHaveBeenCalled();
  });

  it('отказывает файл больше 2 МБ', async () => {
    const { container } = render(
      <AvatarUploader hasAvatar={false} avatarVersion={null} initials="ДА" />,
    );
    const input = container.querySelector('input[type=file]') as HTMLInputElement;
    const big = new File([new Uint8Array(3 * 1024 * 1024)], 'big.png', { type: 'image/png' });
    fireEvent.change(input, { target: { files: [big] } });
    await waitFor(() => expect(toastError).toHaveBeenCalled());
    expect(toastError.mock.calls[0][0]).toMatch(/больше 2 МБ/i);
    expect(apiClientMock).not.toHaveBeenCalled();
  });

  it('успешный upload вызывает POST /api/me/avatar и toast.success', async () => {
    apiClientMock.mockResolvedValueOnce({});
    const { container } = render(
      <AvatarUploader hasAvatar={false} avatarVersion={null} initials="ДА" />,
    );
    const input = container.querySelector('input[type=file]') as HTMLInputElement;
    const file = new File(['png'], 'av.png', { type: 'image/png' });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(apiClientMock).toHaveBeenCalled());
    expect(apiClientMock.mock.calls[0][0]).toBe('/api/me/avatar');
    expect(apiClientMock.mock.calls[0][1].method).toBe('POST');
    expect(apiClientMock.mock.calls[0][1].body).toBeInstanceOf(FormData);
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled());
  });
});
