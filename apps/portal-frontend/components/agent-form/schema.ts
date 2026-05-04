import { z, type ZodTypeAny } from 'zod';
import type { AgentManifest, ManifestInput } from '@/lib/api/types';

function buildFieldSchema(field: ManifestInput): ZodTypeAny {
  switch (field.type) {
    case 'text':
    case 'textarea': {
      let s: z.ZodString = z.string();
      // != null ловит и null и undefined (backend сериализует Optional как null).
      if (field.min_length != null) s = s.min(field.min_length);
      if (field.max_length != null) s = s.max(field.max_length);
      if (field.pattern) {
        try {
          s = s.regex(new RegExp(field.pattern));
        } catch {
          // Invalid regex in manifest — пропускаем constraint, валидация на backend.
        }
      }
      return field.required ? s.min(1, 'Обязательное поле') : s.optional().or(z.literal(''));
    }
    case 'number': {
      let s: z.ZodNumber = z.number();
      if (field.min != null) s = s.min(field.min);
      if (field.max != null) s = s.max(field.max);
      return field.required ? s : s.optional();
    }
    case 'checkbox':
      return z.boolean().optional().default((field.default as boolean) ?? false);
    case 'select':
    case 'radio': {
      const values = field.options?.map((o) => o.value) ?? [];
      const s = values.length > 0 ? z.enum(values as [string, ...string[]]) : z.string();
      return field.required ? s : s.optional().or(z.literal(''));
    }
    case 'date': {
      const s = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD');
      return field.required ? s : s.optional().or(z.literal(''));
    }
    default:
      return z.unknown();
  }
}

export function buildZodSchema(manifest: AgentManifest): z.ZodObject<Record<string, ZodTypeAny>> {
  const shape: Record<string, ZodTypeAny> = {};
  for (const [id, field] of Object.entries(manifest.inputs ?? {})) {
    shape[id] = buildFieldSchema(field);
  }
  return z.object(shape);
}
