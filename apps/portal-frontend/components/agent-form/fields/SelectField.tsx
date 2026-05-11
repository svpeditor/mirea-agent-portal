'use client';
import type { Control, FieldValues, Path } from 'react-hook-form';
import { Controller } from 'react-hook-form';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import type { ManifestInput } from '@/lib/api/types';

interface Props<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  field: ManifestInput;
}

export function SelectField<T extends FieldValues>({ name, control, field }: Props<T>) {
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={(field.default ?? '') as T[Path<T>]}
      render={({ field: rhf, fieldState }) => (
        <div>
          <Label htmlFor={name}>
            {field.label}
            {field.required && <span className="text-[color:var(--color-error)]"> *</span>}
          </Label>
          <Select value={(rhf.value ?? '') as string} onValueChange={rhf.onChange}>
            <SelectTrigger id={name}>
              <SelectValue placeholder={field.placeholder ?? 'Выбери…'} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {field.help && <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">{field.help}</p>}
          {fieldState.error && (
            <p className="mt-1 text-xs text-[color:var(--color-error)]">{fieldState.error.message}</p>
          )}
        </div>
      )}
    />
  );
}
