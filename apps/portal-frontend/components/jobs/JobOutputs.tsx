import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import type { JobOutputFile } from '@/lib/api/types';

interface Props {
  outputs: JobOutputFile[];
  jobId: string;
}

export function JobOutputs({ outputs, jobId }: Props) {
  return (
    <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-4">
      <h3 className="mb-3 font-serif text-lg">Результат</h3>
      <ul className="space-y-2">
        {outputs.map((file) => (
          <li key={file.id}>
            <Button asChild variant="outline" size="sm" className="w-full justify-start">
              <a
                href={`/api/jobs/${jobId}/outputs/${file.id}`}
                download={file.filename}
                className="no-underline"
              >
                <Download className="mr-2 h-4 w-4" />
                {file.filename}
                <span className="ml-auto font-mono text-xs text-[color:var(--color-text-secondary)]">
                  {(file.size_bytes / 1024).toFixed(1)} KB
                </span>
              </a>
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
