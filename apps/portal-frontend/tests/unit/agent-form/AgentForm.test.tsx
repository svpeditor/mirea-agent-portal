import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AgentForm } from '@/components/agent-form/AgentForm';
import type { AgentManifest } from '@/lib/api/types';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function baseManifest(extra: Partial<AgentManifest> = {}): AgentManifest {
  return {
    id: 't',
    name: 'T',
    version: '1',
    category: 'x',
    short_description: '',
    outputs: [],
    runtime: {
      docker: { base_image: 'x', entrypoint: [] },
      limits: { max_runtime_minutes: 1, max_memory_mb: 1, max_cpu_cores: 1 },
    },
    ...extra,
  };
}

function renderForm(manifest: AgentManifest) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <AgentForm manifest={manifest} agentSlug="test" />
    </QueryClientProvider>,
  );
}

describe('AgentForm', () => {
  it('рендерит text-поле', () => {
    renderForm(
      baseManifest({
        inputs: { title: { type: 'text', label: 'Title', required: true } },
      }),
    );
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
  });

  it('рендерит select с options', () => {
    renderForm(
      baseManifest({
        inputs: {
          size: {
            type: 'select',
            label: 'Size',
            options: [
              { value: 'sm', label: 'Small' },
              { value: 'lg', label: 'Large' },
            ],
          },
        },
      }),
    );
    expect(screen.getByText(/Size/i)).toBeInTheDocument();
  });

  it('пустой manifest — кнопка запуска видна', () => {
    renderForm(baseManifest());
    expect(screen.getByRole('button', { name: /Запустить/i })).toBeInTheDocument();
  });
});
