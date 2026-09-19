import Link from "next/link";

import {
  CacheSection,
  MemorySection,
  ModelSection,
  RetrievalSection,
} from "@/components/context/component-sections";
import { ContextBudget } from "@/components/context/context-budget";
import { SignalPath } from "@/components/context/signal-path";
import { StatusGlyph } from "@/components/status";
import { configLabel } from "@/lib/components";
import { formatClock, formatMs } from "@/lib/format";
import type { ExecutionRecord } from "@/types/api";

/**
 * The Context Inspector: one execution record, laid out in the order the
 * question gets asked. Which path did it take, what reached the model, and
 * then each component's own account of what it did.
 */
export function Inspector({
  record,
  pending = false,
}: {
  record: ExecutionRecord | undefined;
  pending?: boolean;
}) {
  if (!record) {
    return (
      <div className="flex flex-col gap-6">
        <div>
          <h2 className="text-[15px] font-bold">Execution record</h2>
          <p className="mt-1 max-w-prose text-sm text-ink-soft">
            {pending
              ? "Running the pipeline…"
              : "Send a message and its record appears here: the path it took through each component, the context that reached the model, and what every step cost."}
          </p>
        </div>
        <SignalPath record={undefined} />
      </div>
    );
  }

  return (
    <div aria-busy={pending} className={`transition-opacity ${pending ? "opacity-45" : ""}`}>
      <header className="flex flex-wrap items-start gap-x-6 gap-y-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg leading-snug font-bold tracking-[-0.01em] text-balance">
            “{record.message}”
          </h2>
          <p className="mt-1 flex flex-wrap gap-x-3 text-[13px] text-ink-faint">
            <span className="font-mono">{record.request_id}</span>
            <span>{formatClock(record.started_at)}</span>
            <span>{configLabel(record.execution_config)}</span>
          </p>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-2xl leading-none font-bold tracking-[-0.02em]">
            {formatMs(record.total_duration_ms)}
          </span>
          <Link
            href={`/analytics/${record.request_id}`}
            className="mt-1.5 rounded text-[13px] text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
          >
            Open replay
          </Link>
        </div>
      </header>

      <div className="mt-6">
        <SignalPath record={record} />
      </div>

      <InspectorDetails record={record} />
    </div>
  );
}

/** Everything below the path: what reached the model, then each component's account. */
export function InspectorDetails({ record }: { record: ExecutionRecord }) {
  return (
    <>
      {record.cache.hit && (
        <p className="mt-5 rounded-lg bg-surface-sunk px-3 py-2 text-sm text-ink-soft">
          Served from the cache. Memory, retrieval, and the model were skipped, which is the saving
          the cache exists to produce.
        </p>
      )}

      {record.error && (
        <p role="alert" className="mt-5 flex items-start gap-2 text-sm text-critical-ink">
          <StatusGlyph kind="unavailable" className="mt-1 size-2.5" />
          {record.error}
        </p>
      )}

      <div className="mt-4">
        <ContextBudget context={record.context} cacheHit={record.cache.hit} />
        <CacheSection record={record} />
        <MemorySection record={record} />
        <RetrievalSection record={record} />
        <ModelSection record={record} />
      </div>
    </>
  );
}
