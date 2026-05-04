'use client';
import type { Control, FieldValues, Path } from 'react-hook-form';
import { Controller } from 'react-hook-form';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import type { ManifestInput } from '@/lib/api/types';

interface Props<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  field: ManifestInput;
}

export function CheckboxField<T extends FieldValues>({ name, control, field }: Props<T>) {
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={((field.default as boolean) ?? false) as T[Path<T>]}
      render={({ field: rhf, fieldState }) => (
        <div>
          <div className="flex items-center gap-2">
            <Checkbox
              id={name}
              checked={Boolean(rhf.value)}
              onCheckedChange={(checked) => rhf.onChange(Boolean(checked))}
            />
            <Label htmlFor={name} className="cursor-pointer">
              {field.label}
              {field.required && <span className="text-[color:var(--color-error)]"> *</span>}
            </Label>
          </div>
          {field.help && <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">{field.help}</p>}
          {fieldState.error && (
            <p className="mt-1 text-xs text-[color:var(--color-error)]">{fieldState.error.message}</p>
          )}
        </div>
      )}
    />
  );
}
