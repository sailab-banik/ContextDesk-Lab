"use client";

import Link from "next/link";

import { StepWaterfall } from "@/components/analytics/step-waterfall";
import { BackendNotice } from "@/components/backend-notice";
import { InspectorDetails } from "@/components/context/inspector";
import { useBackendResource } from "@/hooks/use-backend-resource";
import { api } from "@/lib/api";
import { configLabel } from "@/lib/components";
import { formatClock, formatMs } from "@/lib/format";

export function ReplayView({ requestId }: { requestId: string }) {
  const replay = useBackendResource(`record:${requestId}`, () => api.record(requestId));
  const record = replay.data;

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-8 sm:py-10">
      <Link
        href="/analytics"
        className="rounded text-sm text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
      >
        Back to analytics
      </Link>

      {replay.error && (
        <div className="mt-6">
          <BackendNotice error={replay.error} onRetry={replay.reload} />
        </div>
      )}

      {!record && replay.status === "loading" && (
        <p className="mt-6 text-sm text-ink-soft">Loading the record…</p>
      )}

      {record && (
        <>
          <header className="mt-5 flex flex-wrap items-start justify-between gap-x-8 gap-y-3">
            <div className="min-w-0">
              <h1 className="text-3xl leading-tight font-bold tracking-[-0.02em] text-balance">
                “{record.message}”
              </h1>
              <p className="mt-2 flex flex-wrap gap-x-4 text-sm text-ink-soft">
                <span className="font-mono text-[13px]">{record.request_id}</span>
                <span>{formatClock(record.started_at)}</span>
                <span>{configLabel(record.execution_config)}</span>
                <span>
                  Customer <span className="font-mono text-[13px]">{record.user_id}</span>
                </span>
              </p>
            </div>
            <p className="text-right">
              <span className="block text-3xl leading-none font-bold tracking-[-0.02em]">
                {formatMs(record.total_duration_ms)}
              </span>
              <span className="text-sm text-ink-faint">total</span>
            </p>
          </header>

          <section className="mt-8">
            <h2 className="mb-3 text-[15px] font-bold">Steps, in the order they ran</h2>
            <StepWaterfall record={record} />
          </section>

          <section className="mt-8">
            <h2 className="text-[15px] font-bold">Response</h2>
            <p className="mt-2 max-w-prose rounded-lg border border-rule bg-surface px-4 py-3 text-[15px] leading-6 whitespace-pre-wrap">
              {record.response || "No response was produced."}
            </p>
          </section>

          <div className="mt-4">
            <InspectorDetails record={record} />
          </div>
        </>
      )}
    </main>
  );
}
