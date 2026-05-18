'use client';
import * as React from 'react';
import type {
  Control,
  ControllerRenderProps,
  FieldValues,
  Path,
} from 'react-hook-form';
import { Controller } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { ManifestInput } from '@/lib/api/types';

interface Props<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  field: ManifestInput;
}

// Модульный компонент (стабильная идентичность => локальный стейт живёт
// между рендерами). Строковый ввод вместо type="number": браузерный
// number-input отбрасывает пустые/промежуточные состояния, из-за чего
// нельзя стереть последнюю цифру. Сырую строку держим локально, в RHF
// кладём число (или undefined для пустого) — min/max валидирует zod.
function NumberInput({
  id,
  placeholder,
  rhf,
}: {
  id: string;
  placeholder?: string;
  rhf: ControllerRenderProps<FieldValues, string>;
}) {
  const [raw, setRaw] = React.useState<string>(
    rhf.value == null ? '' : String(rhf.value),
  );
  // Внешний reset формы — подхватываем, но не перетираем то, что юзер печатает.
  React.useEffect(() => {
    const ext = rhf.value == null ? '' : String(rhf.value);
    if (ext !== raw && document.activeElement?.id !== id) setRaw(ext);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rhf.value]);

  return (
    <Input
      id={id}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      placeholder={placeholder}
      value={raw}
      onChange={(e) => {
        const v = e.target.value;
        // цифры + опциональный ведущий - и одна десятичная точка
        // (манифест допускает float min/max/step)
        if (v !== '' && !/^-?\d*\.?\d*$/.test(v)) return;
        setRaw(v);
        const n = Number(v);
        rhf.onChange(
          v === '' || v === '-' || v === '.' || v === '-.' || Number.isNaN(n)
            ? undefined
            : n,
        );
      }}
      onBlur={rhf.onBlur}
      ref={rhf.ref}
      name={rhf.name}
    />
  );
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
            {field.required && (
              <span className="text-[color:var(--color-error)]"> *</span>
            )}
          </Label>
          <NumberInput
            id={name}
            placeholder={field.placeholder}
            rhf={rhf as unknown as ControllerRenderProps<FieldValues, string>}
          />
          {field.help && (
            <p className="mt-1 text-xs text-[color:var(--color-text-secondary)]">
              {field.help}
            </p>
          )}
          {fieldState.error && (
            <p className="mt-1 text-xs text-[color:var(--color-error)]">
              {fieldState.error.message}
            </p>
          )}
        </div>
      )}
    />
  );
}
