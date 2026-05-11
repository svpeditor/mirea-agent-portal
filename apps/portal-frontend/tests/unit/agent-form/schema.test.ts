import { describe, it, expect } from 'vitest';
import { buildZodSchema } from '@/components/agent-form/schema';
import type { AgentManifest } from '@/lib/api/types';

describe('buildZodSchema', () => {
  it('создаёт схему для text-поля', () => {
    const manifest: Partial<AgentManifest> = {
      inputs: {
        title: { type: 'text', label: 'Title', required: true, max_length: 100 },
      },
    };
    const schema = buildZodSchema(manifest as AgentManifest);
    expect(schema.safeParse({ title: 'Hello' }).success).toBe(true);
    expect(schema.safeParse({ title: '' }).success).toBe(false);
    expect(schema.safeParse({ title: 'x'.repeat(101) }).success).toBe(false);
  });

  it('обрабатывает number с min/max', () => {
    const manifest: Partial<AgentManifest> = {
      inputs: {
        age: { type: 'number', label: 'Age', min: 0, max: 100 },
      },
    };
    const schema = buildZodSchema(manifest as AgentManifest);
    expect(schema.safeParse({ age: 50 }).success).toBe(true);
    expect(schema.safeParse({ age: -1 }).success).toBe(false);
    expect(schema.safeParse({ age: 101 }).success).toBe(false);
  });

  it('обрабатывает select с options', () => {
    const manifest: Partial<AgentManifest> = {
      inputs: {
        size: {
          type: 'select',
          label: 'Size',
          required: true,
          options: [
            { value: 'sm', label: 'Small' },
            { value: 'lg', label: 'Large' },
          ],
        },
      },
    };
    const schema = buildZodSchema(manifest as AgentManifest);
    expect(schema.safeParse({ size: 'sm' }).success).toBe(true);
    expect(schema.safeParse({ size: 'xl' }).success).toBe(false);
  });

  it('checkbox optional если default есть', () => {
    const manifest: Partial<AgentManifest> = {
      inputs: {
        agree: { type: 'checkbox', label: 'Agree', default: false },
      },
    };
    const schema = buildZodSchema(manifest as AgentManifest);
    expect(schema.safeParse({ agree: true }).success).toBe(true);
    expect(schema.safeParse({ agree: false }).success).toBe(true);
  });

  it('пустой manifest — пустая схема', () => {
    const manifest: Partial<AgentManifest> = {};
    const schema = buildZodSchema(manifest as AgentManifest);
    expect(schema.safeParse({}).success).toBe(true);
  });
});
