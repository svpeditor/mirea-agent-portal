'use client';
import type { Control, FieldValues, Path } from 'react-hook-form';
import { Controller } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { ManifestInput } from '@/lib/api/types';

interface Props<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  field: ManifestInput;
}

export function NumberField<T extends FieldValues>({ name, control, field }: Props<T>) {
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={(field.default ?? undefined) as T[Path<T>]}
      render={({ field: rhf, fieldState }) => (
        <div>
          <Label htmlFor={name}>
            {field.label}
            {field.required && <span className="text-[color:var(--color-error)]"> *</span>}
          </Label>
          <Input
            id={name}
            type="number"
            placeholder={field.placeholder}
            value={(rhf.value ?? '') as string | number}
            min={field.min}
            max={field.max}
            step={field.step}
            onChange={(e) => rhf.onChange(e.target.value === '' ? undefined : Number(e.target.value))}
            onBlur={rhf.onBlur}
            ref={rhf.ref}
            name={rhf.name}
          />
          {field.help && <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">{field.help}</p>}
          {fieldState.error && (
            <p className="mt-1 text-xs text-[color:var(--color-error)]">{fieldState.error.message}</p>
          )}
        </div>
      )}
    />
  );
}
