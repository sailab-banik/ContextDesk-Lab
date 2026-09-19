import type {
  AnalyticsSummary,
  ChatRequest,
  ChatResponse,
  ComparisonResponse,
  ExecutionRecord,
  HealthResponse,
  HistoryPage,
} from "@/types/api";

// The backend's CORS policy only admits the dev frontend, so the pairing is a
// local-development convention; set NEXT_PUBLIC_API_URL to point elsewhere.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class BackendError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "content-type": "application/json", ...init?.headers },
    });
  } catch {
    // A network failure means the backend is not running, which is the most
    // common state for a local tool. Say how to fix it rather than "failed to fetch".
    throw new BackendError(
      `Can't reach the backend at ${API_URL}. Start it with: cd backend && uv run fastapi dev app/main.py`,
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new BackendError(`The backend returned ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  sendMessage: (body: ChatRequest) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(body) }),

  compare: (message: string) =>
    request<ComparisonResponse>("/api/chat/compare", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  summary: () => request<AnalyticsSummary>("/api/analytics/summary"),

  history: (limit = 200) => request<HistoryPage>(`/api/analytics/history?limit=${limit}`),

  record: (requestId: string) =>
    request<ExecutionRecord>(`/api/analytics/history/${encodeURIComponent(requestId)}`),
};

export function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
