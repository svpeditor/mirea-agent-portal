import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FileUpload } from '@/components/agent-form/FileUpload';
import type { ManifestFile } from '@/lib/api/types';

describe('FileUpload', () => {
  it('single_file — принимает один файл', () => {
    const onChange = vi.fn();
    const fileSpec: ManifestFile = { type: 'single_file', label: 'PDF', accept: ['.pdf'] };
    render(<FileUpload name="f" fileSpec={fileSpec} onFilesChange={onChange} />);

    const input = screen.getByLabelText(/PDF/i) as HTMLInputElement;
    const file = new File(['content'], 'doc.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onChange).toHaveBeenCalledWith([file]);
  });

  it('multi_files — принимает несколько файлов', () => {
    const onChange = vi.fn();
    const fileSpec: ManifestFile = { type: 'multi_files', label: 'Docs' };
    render(<FileUpload name="d" fileSpec={fileSpec} onFilesChange={onChange} />);

    const input = screen.getByLabelText(/Docs/i) as HTMLInputElement;
    const files = [new File(['a'], 'a.txt'), new File(['b'], 'b.txt')];
    fireEvent.change(input, { target: { files } });
    expect(onChange).toHaveBeenCalledWith(files);
  });

  it('помечает required', () => {
    const fileSpec: ManifestFile = { type: 'single_file', label: 'PDF', required: true };
    render(<FileUpload name="f" fileSpec={fileSpec} onFilesChange={vi.fn()} />);
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('показывает имя выбранного файла', () => {
    const fileSpec: ManifestFile = { type: 'single_file', label: 'PDF' };
    render(<FileUpload name="f" fileSpec={fileSpec} onFilesChange={vi.fn()} />);
    const input = screen.getByLabelText(/PDF/i) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File([''], 'report.pdf')] } });
    expect(screen.getByText(/report\.pdf/)).toBeInTheDocument();
  });
});
