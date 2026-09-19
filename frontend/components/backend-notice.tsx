import { StatusGlyph } from "@/components/status";

/** A failed backend call, said plainly, with the one action that can fix it. */
export function BackendNotice({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-critical/40 px-4 py-3 text-sm">
      <StatusGlyph kind="unavailable" className="mt-1 size-2.5" />
      <p className="flex-1 text-critical-ink">{error}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md px-2 py-0.5 text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
        >
          Retry
        </button>
      )}
    </div>
  );
}
