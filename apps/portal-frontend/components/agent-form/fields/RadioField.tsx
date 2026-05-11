'use client';
import type { Control, FieldValues, Path } from 'react-hook-form';
import { Controller } from 'react-hook-form';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import type { ManifestInput } from '@/lib/api/types';

interface Props<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  field: ManifestInput;
}

export function RadioField<T extends FieldValues>({ name, control, field }: Props<T>) {
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={(field.default ?? '') as T[Path<T>]}
      render={({ field: rhf, fieldState }) => {
        const groupLabelId = `${name}-label`;
        return (
        <div>
          <Label id={groupLabelId}>
            {field.label}
            {field.required && <span className="text-[color:var(--color-error)]"> *</span>}
          </Label>
          <RadioGroup
            aria-labelledby={groupLabelId}
            value={(rhf.value ?? '') as string}
            onValueChange={rhf.onChange}
            className="mt-2 space-y-2"
          >
            {field.options?.map((opt) => (
              <div key={opt.value} className="flex items-center gap-2">
                <RadioGroupItem id={`${name}-${opt.value}`} value={opt.value} />
                <Label htmlFor={`${name}-${opt.value}`} className="cursor-pointer font-normal">
                  {opt.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
          {field.help && <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">{field.help}</p>}
          {fieldState.error && (
            <p className="mt-1 text-xs text-[color:var(--color-error)]">{fieldState.error.message}</p>
          )}
        </div>
        );
      }}
    />
  );
}
