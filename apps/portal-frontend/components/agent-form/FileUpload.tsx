'use client';
import { useState, useRef } from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Upload, X } from 'lucide-react';
import type { ManifestFile } from '@/lib/api/types';
import { toast } from 'sonner';

interface Props {
  name: string;
  fileSpec: ManifestFile;
  onFilesChange: (files: File[]) => void;
}

export function FileUpload({ name, fileSpec, onFilesChange }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const isMulti = fileSpec.type === 'multi_files' || fileSpec.type === 'folder';
  const acceptStr = fileSpec.accept?.join(',');

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const newFiles = Array.from(e.target.files ?? []);
    if (newFiles.length === 0) return;

    if (fileSpec.max_total_size_mb) {
      const totalBytes = newFiles.reduce((s, f) => s + f.size, 0);
      const maxBytes = fileSpec.max_total_size_mb * 1024 * 1024;
      if (totalBytes > maxBytes) {
        toast.error(`Превышен размер: ${fileSpec.max_total_size_mb} MB`);
        return;
      }
    }

    setFiles(newFiles);
    onFilesChange(newFiles);
  }

  function removeAll() {
    setFiles([]);
    onFilesChange([]);
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div>
      <Label htmlFor={name}>
        {fileSpec.label}
        {fileSpec.required && <span className="text-[color:var(--color-error)]"> *</span>}
      </Label>
      <div className="mt-1">
        <input
          ref={inputRef}
          id={name}
          type="file"
          multiple={isMulti}
          accept={acceptStr}
          {...(fileSpec.type === 'folder' ? ({ webkitdirectory: '' } as React.InputHTMLAttributes<HTMLInputElement>) : {})}
          onChange={handleChange}
          className="sr-only"
        />
        {files.length === 0 ? (
          <Button type="button" variant="outline" className="w-full" onClick={() => inputRef.current?.click()}>
            <Upload className="mr-2 h-4 w-4" />
            Выбрать {isMulti ? 'файлы' : 'файл'}
          </Button>
        ) : (
          <div className="rounded-md border border-[color:var(--color-border)] p-3">
            <ul className="space-y-1 text-sm">
              {files.map((f) => (
                <li key={f.name} className="flex justify-between">
                  <span>{f.name}</span>
                  <span className="text-[color:var(--color-text-secondary)]">{(f.size / 1024).toFixed(1)} KB</span>
                </li>
              ))}
            </ul>
            <Button type="button" variant="ghost" size="sm" onClick={removeAll} className="mt-2">
              <X className="mr-1 h-3 w-3" />
              Очистить
            </Button>
          </div>
        )}
      </div>
      {fileSpec.help && <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">{fileSpec.help}</p>}
    </div>
  );
}
