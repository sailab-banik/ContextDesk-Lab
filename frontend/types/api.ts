// Mirrors backend/app/models. The execution record's shape already matches the
// inspector's sections, so the UI reads it as-is instead of reassembling it.

export type ComponentStatus = "ok" | "stub" | "unavailable" | "disabled";

export type ComponentName = "memory" | "retrieval" | "cache" | "llm";

export type ExclusionReason =
  | "no_data"
  | "not_relevant"
  | "below_relevance_threshold"
  | "context_budget_exceeded"
  | "component_disabled"
  | "component_unavailable";

export interface ExecutionConfig {
  memory_enabled: boolean;
  retrieval_enabled: boolean;
  cache_enabled: boolean;
}

export interface MemoryEntry {
  id: string;
  text: string;
  created_at: string | null;
  topics: string[];
  relevance: number | null;
  origin: string;
}

export interface RetrievedSource {
  name: string;
  tool: string;
  arguments: Record<string, string | number>;
  records: Record<string, unknown>[];
  duration_ms: number;
  status: ComponentStatus;
  error: string | null;
}

export interface ContextSection {
  name: string;
  origin: string;
  content: string;
  estimated_tokens: number;
}

export interface ExcludedContext {
  name: string;
  origin: string;
  reason: ExclusionReason;
  estimated_tokens: number;
  detail: string | null;
}

export interface MemoryReport {
  status: ComponentStatus;
  duration_ms: number;
  entries: MemoryEntry[];
  used_count: number;
  skipped_reason: string | null;
  error: string | null;
}

export interface RetrievalReport {
  status: ComponentStatus;
  duration_ms: number;
  sources: RetrievedSource[];
  skipped_reason: string | null;
  error: string | null;
}

export interface CacheReport {
  status: ComponentStatus;
  duration_ms: number;
  hit: boolean;
  similarity: number | null;
  matched_prompt: string | null;
  threshold: number | null;
  stored: boolean;
  skipped_reason: string | null;
  error: string | null;
}

export interface LLMReport {
  status: ComponentStatus;
  called: boolean;
  duration_ms: number;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  skipped_reason: string | null;
  error: string | null;
}

export interface ContextSummary {
  sources: string[];
  size_chars: number;
  estimated_tokens: number;
  budget_tokens: number;
  included: ContextSection[];
  excluded: ExcludedContext[];
}

export interface ExecutionStep {
  name: string;
  status: ComponentStatus;
  duration_ms: number;
  detail: string;
}

export interface ExecutionRecord {
  request_id: string;
  user_id: string;
  session_id: string;
  message: string;
  response: string;
  started_at: string;
  completed_at: string | null;
  total_duration_ms: number;
  execution_config: ExecutionConfig;
  memory: MemoryReport;
  retrieval: RetrievalReport;
  cache: CacheReport;
  llm: LLMReport;
  context: ContextSummary;
  steps: ExecutionStep[];
  error: string | null;
}

export interface ChatRequest {
  message: string;
  user_id?: string;
  session_id?: string;
  config: ExecutionConfig;
}

export interface ChatResponse {
  response: string;
  execution: ExecutionRecord;
}

export interface ComparisonRun {
  label: string;
  config: ExecutionConfig;
  response: string;
  execution: ExecutionRecord;
}

export interface ComparisonResponse {
  message: string;
  runs: ComparisonRun[];
}

export interface ComponentHealth {
  name: ComponentName;
  status: ComponentStatus;
  detail: string;
}

export interface HealthResponse {
  status: string;
  components: ComponentHealth[];
}

export interface AnalyticsSummary {
  latency: {
    average_ms: number;
    p50_ms: number;
    p95_ms: number;
    average_llm_ms: number;
    average_cache_hit_ms: number;
  };
  cache: {
    hit_rate: number;
    hits: number;
    misses: number;
    average_lookup_ms: number;
    llm_calls_avoided: number;
  };
  llm: {
    total_requests: number;
    total_llm_calls: number;
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
    estimated_saved_usd: number;
  };
  context: {
    memory_used: number;
    retrieval_used: number;
    cache_used: number;
    average_context_tokens: number;
    sources_used: Record<string, number>;
  };
  cost_is_estimated: boolean;
}

export interface ExecutionSummary {
  request_id: string;
  started_at: string;
  user_id: string;
  message: string;
  config_label: string;
  memory_status: ComponentStatus;
  retrieval_status: ComponentStatus;
  cache_status: ComponentStatus;
  cache_hit: boolean;
  llm_called: boolean;
  total_duration_ms: number;
  context_tokens: number;
}

export interface HistoryPage {
  items: ExecutionSummary[];
  total: number;
}
