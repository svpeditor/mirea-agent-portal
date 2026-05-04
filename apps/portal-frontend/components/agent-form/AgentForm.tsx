'use client';
import * as React from 'react';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { toast } from 'sonner';
import type { AgentManifest } from '@/lib/api/types';
import { ApiError, type ApiErrorBody } from '@/lib/api/types';

interface JobCreatedResponse {
  job: { id: string; status: string; agent_slug: string };
}
import { buildZodSchema } from './schema';
import { TextField } from './fields/TextField';
import { TextareaField } from './fields/TextareaField';
import { NumberField } from './fields/NumberField';
import { CheckboxField } from './fields/CheckboxField';
import { SelectField } from './fields/SelectField';
import { RadioField } from './fields/RadioField';
import { DateField } from './fields/DateField';
import { FileUpload } from './FileUpload';
import { Button } from '@/components/ui/button';
import { mapApiError } from '@/lib/api/errors';

interface Props {
  manifest: AgentManifest;
  agentSlug: string;
}

const FIELD_COMPONENTS = {
  text: TextField,
  textarea: TextareaField,
  number: NumberField,
  checkbox: CheckboxField,
  select: SelectField,
  radio: RadioField,
  date: DateField,
} as const;

function collectDefaults(manifest: AgentManifest): Record<string, unknown> {
  const defaults: Record<string, unknown> = {};
  for (const [id, field] of Object.entries(manifest.inputs ?? {})) {
    if (field.default !== undefined) defaults[id] = field.default;
  }
  return defaults;
}

export function AgentForm({ manifest, agentSlug }: Props) {
  const router = useRouter();
  const schema = React.useMemo(() => buildZodSchema(manifest), [manifest]);
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: collectDefaults(manifest),
  });

  const [filesByKey, setFilesByKey] = React.useState<Record<string, File[]>>({});

  const mutation = useMutation({
    mutationFn: async (data: { params: Record<string, unknown>; files: Record<string, File[]> }) => {
      const formData = new FormData();
      formData.append('params', JSON.stringify(data.params));
      for (const [key, files] of Object.entries(data.files)) {
        for (const file of files) {
          formData.append(key, file);
        }
      }
      const res = await fetch(`/api/agents/${agentSlug}/jobs`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });
      if (!res.ok) {
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          /* ignore parse error */
        }
        throw new ApiError(res.status, body as ApiErrorBody | null);
      }
      return (await res.json()) as JobCreatedResponse;
    },
    onSuccess: (data) => {
      router.push(`/jobs/${data.job.id}` as Route);
    },
    onError: (err) => {
      toast.error(mapApiError(err));
    },
  });

  const onSubmit: SubmitHandler<Record<string, unknown>> = (params) => {
    for (const [key, fileSpec] of Object.entries(manifest.files ?? {})) {
      if (fileSpec.required && (!filesByKey[key] || filesByKey[key].length === 0)) {
        toast.error(`Загрузи файл для «${fileSpec.label}»`);
        return;
      }
    }
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== undefined),
    );
    mutation.mutate({ params: cleanParams, files: filesByKey });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
      {Object.entries(manifest.inputs ?? {}).map(([id, field]) => {
        const FieldComp = FIELD_COMPONENTS[field.type];
        if (!FieldComp) return null;
        return <FieldComp key={id} name={id} control={form.control} field={field} />;
      })}
      {Object.entries(manifest.files ?? {}).map(([id, fileSpec]) => (
        <FileUpload
          key={id}
          name={id}
          fileSpec={fileSpec}
          onFilesChange={(files) => setFilesByKey((prev) => ({ ...prev, [id]: files }))}
        />
      ))}
      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? 'Запускаю...' : 'Запустить агента'}
      </Button>
    </form>
  );
}
