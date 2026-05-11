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
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const isMulti = fileSpec.type === 'multi_files' || fileSpec.type === 'folder';
  const isFolder = fileSpec.type === 'folder';
  const acceptStr = fileSpec.accept?.join(',');

  function applyFiles(newFiles: File[]) {
    if (newFiles.length === 0) return;
    if (fileSpec.max_total_size_mb) {
      const totalBytes = newFiles.reduce((s, f) => s + f.size, 0);
      const maxBytes = fileSpec.max_total_size_mb * 1024 * 1024;
      if (totalBytes > maxBytes) {
        toast.error(`Превышен размер: ${fileSpec.max_total_size_mb} MB`);
        if (inputRef.current) inputRef.current.value = '';
        return;
      }
    }
    if (fileSpec.accept && fileSpec.accept.length > 0) {
      const exts = fileSpec.accept.map((e) => e.toLowerCase());
      const bad = newFiles.find((f) => {
        const name = f.name.toLowerCase();
        return !exts.some((e) => name.endsWith(e));
      });
      if (bad) {
        toast.error(`Файл ${bad.name} не соответствует ${fileSpec.accept.join(', ')}`);
        return;
      }
    }
    setFiles(newFiles);
    onFilesChange(newFiles);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    applyFiles(Array.from(e.target.files ?? []));
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files ?? []);
    if (isFolder) {
      // Folder drop: webkitGetAsEntry для рекурсивного обхода.
      const items = Array.from(e.dataTransfer.items ?? []);
      const entries = items
        .map((it) => (typeof it.webkitGetAsEntry === 'function' ? it.webkitGetAsEntry() : null))
        .filter((x): x is FileSystemEntry => x !== null);
      if (entries.length > 0) {
        walkEntries(entries).then(applyFiles).catch((err) => toast.error(String(err)));
        return;
      }
    }
    applyFiles(isMulti ? dropped : dropped.slice(0, 1));
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
          {...(isFolder ? ({ webkitdirectory: '' } as React.InputHTMLAttributes<HTMLInputElement>) : {})}
          onChange={handleChange}
          className="sr-only"
        />
        {files.length === 0 ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            className={`flex w-full cursor-pointer flex-col items-center justify-center border-2 border-dashed px-6 py-8 transition-colors ${
              dragOver
                ? 'border-[color:var(--color-accent)] bg-[color:var(--color-bg-tertiary)]'
                : 'border-[color:var(--color-rule-mute)] hover:border-[color:var(--color-text-primary)] hover:bg-[color:var(--color-bg-tertiary)]'
            }`}
          >
            <Upload className="mb-2 h-5 w-5 text-[color:var(--color-text-secondary)]" strokeWidth={1.5} />
            <span className="font-mono text-xs uppercase tracking-wider text-[color:var(--color-text-secondary)]">
              {dragOver
                ? 'отпустите чтобы добавить'
                : `перетащите ${isFolder ? 'папку' : isMulti ? 'файлы' : 'файл'} или нажмите`}
            </span>
            {fileSpec.accept && fileSpec.accept.length > 0 && (
              <span className="mt-1 font-mono text-[10px] text-[color:var(--color-text-tertiary)]">
                {fileSpec.accept.join(' · ')}
              </span>
            )}
          </div>
        ) : (
          <div className="rounded-md border border-[color:var(--color-border)] p-3">
            <ul className="space-y-1 text-sm">
              {files.slice(0, 20).map((f) => (
                <li key={`${f.name}-${f.size}`} className="flex justify-between">
                  <span>{f.webkitRelativePath || f.name}</span>
                  <span className="text-[color:var(--color-text-secondary)]">
                    {(f.size / 1024).toFixed(1)} KB
                  </span>
                </li>
              ))}
              {files.length > 20 && (
                <li className="italic text-[color:var(--color-text-secondary)]">
                  …и ещё {files.length - 20}
                </li>
              )}
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

// Рекурсивный обход webkitGetAsEntry — для folder drop.
async function walkEntries(entries: FileSystemEntry[]): Promise<File[]> {
  const result: File[] = [];

  async function walk(entry: FileSystemEntry, prefix: string): Promise<void> {
    if (entry.isFile) {
      const file = await new Promise<File>((resolve, reject) =>
        (entry as FileSystemFileEntry).file(resolve, reject),
      );
      const path = prefix ? `${prefix}/${file.name}` : file.name;
      // monkey-patch path так чтобы downstream видел webkitRelativePath
      Object.defineProperty(file, 'webkitRelativePath', { value: path, configurable: true });
      result.push(file);
    } else if (entry.isDirectory) {
      const reader = (entry as FileSystemDirectoryEntry).createReader();
      const children = await new Promise<FileSystemEntry[]>((resolve, reject) =>
        reader.readEntries(resolve, reject),
      );
      const subprefix = prefix ? `${prefix}/${entry.name}` : entry.name;
      for (const c of children) await walk(c, subprefix);
    }
  }

  for (const e of entries) await walk(e, '');
  return result;
}
