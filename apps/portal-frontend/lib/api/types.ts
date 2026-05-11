// Auto-gen из openapi.json. До регенерации — минимальный набор.
// Запусти `npm run codegen` после первого запуска backend.

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  role: 'user' | 'admin';
  monthly_budget_usd: string;  // Decimal as string
  has_avatar: boolean;
  avatar_version: string | null;
  created_at: string;
}

export interface UserMeOut extends UserOut {
  quota: UserQuotaOut | null;
}

export interface UserQuotaOut {
  monthly_limit_usd: string;  // Decimal as string в JSON
  period_used_usd: string;
  period_starts_at: string;
  per_job_cap_usd: string;
}

export interface TabOut {
  id: string;
  slug: string;
  name: string;
  order_idx: number;
}

export interface AgentTabBrief {
  slug: string;
  name: string;
}

export interface AgentCurrentVersionBrief {
  id: string;
  manifest_version: string;
  git_sha: string;
}

export interface AgentPublicOut {
  id: string;
  slug: string;
  name: string;
  icon: string | null;
  short_description: string;
  tab: AgentTabBrief;
  current_version: AgentCurrentVersionBrief;
}

export interface AgentDetailOut extends AgentPublicOut {
  manifest: AgentManifest;
}

export interface AgentManifest {
  id: string;
  name: string;
  version: string;
  category: string;
  short_description: string;
  about?: string;
  inputs?: Record<string, ManifestInput>;
  files?: Record<string, ManifestFile>;
  outputs: ManifestOutput[];
  runtime: ManifestRuntime;
}

export interface ManifestInput {
  type: 'text' | 'textarea' | 'number' | 'checkbox' | 'select' | 'radio' | 'date';
  label: string;
  help?: string;
  required?: boolean;
  default?: string | number | boolean;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label: string }>;
  pattern?: string;
  min_length?: number;
  max_length?: number;
  rows?: number;
}

export interface ManifestFile {
  type: 'single_file' | 'multi_files' | 'folder' | 'zip';
  label: string;
  help?: string;
  required?: boolean;
  accept?: string[];
  max_total_size_mb?: number;
}

export interface ManifestOutput {
  id: string;
  type: 'docx' | 'pdf' | 'xlsx' | 'zip' | 'html' | 'json' | 'any';
  label: string;
  filename: string;
  primary?: boolean;
}

export interface ManifestRuntime {
  docker: { base_image: string; setup?: string[]; entrypoint: string[] };
  llm?: { provider: 'openrouter'; models: string[] };
  limits: { max_runtime_minutes: number; max_memory_mb: number; max_cpu_cores: number };
}

export interface JobListItemOut {
  id: string;
  status: JobStatus;
  agent_version_id: string;
  /** Из backend PR #7 — может отсутствовать пока PR не замержен. */
  agent_slug?: string | null;
  agent_name?: string | null;
  cost_usd_total?: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
}

// Backend использует 'ready' для успешного job (не 'succeeded'). Frontend оставлю
// оба значения чтобы badge/streaming работали независимо от того какое из них
// придёт; primary по контракту — 'ready'.
export type JobStatus = 'queued' | 'running' | 'ready' | 'succeeded' | 'failed' | 'cancelled' | 'timed_out';

export interface JobAgentBrief {
  slug: string;
  name: string;
}

export interface JobDetailOut {
  id: string;
  status: JobStatus;
  agent_version_id: string;
  agent: JobAgentBrief;
  params: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  error_code: string | null;
  error_msg: string | null;
  output_summary: Record<string, unknown> | null;
  events_count: number;
  last_event_seq: number | null;
  created_at: string;
}

export interface JobOutputFile {
  id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
}

export interface JobEventOut {
  seq: number;
  ts: string;
  type: 'started' | 'progress' | 'item_done' | 'log' | 'result' | 'failed' | 'error';
  payload: Record<string, unknown>;
}

export interface UsageLogItem {
  id: string;
  job_id: string;
  agent_slug: string | null;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: string;
  status: string;
  created_at: string;
}

export interface UsagePage {
  items: UsageLogItem[];
  next_cursor: string | null;
}

export interface AdminUsageSummary {
  total_cost_usd: string;
  total_requests: number;
  by_user: Array<{ user_id: string; email: string; cost_usd: string; requests: number }>;
  by_agent: Array<{ agent_id: string; slug: string; cost_usd: string; requests: number }>;
  by_model: Array<{ model: string; cost_usd: string; requests: number }>;
}

// Errors
export interface ApiErrorBody {
  error: { code: string; message: string };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ApiErrorBody | null,
  ) {
    super(body?.error?.message ?? `HTTP ${status}`);
    this.name = 'ApiError';
  }
}
