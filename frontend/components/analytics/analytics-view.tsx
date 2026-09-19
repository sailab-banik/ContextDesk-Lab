"use client";

import Link from "next/link";

import { HistoryTable } from "@/components/analytics/history-table";
import { LatencyChart } from "@/components/analytics/latency-chart";
import { MetricGroups } from "@/components/analytics/metric-groups";
import { SourcesChart } from "@/components/analytics/sources-chart";
import { BackendNotice } from "@/components/backend-notice";
import { useBackendResource } from "@/hooks/use-backend-resource";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";

async function loadAnalytics() {
  const [summary, history] = await Promise.all([api.summary(), api.history()]);
  return { summary, history };
}

export function AnalyticsView() {
  const analytics = useBackendResource("analytics", loadAnalytics);
  const data = analytics.data;
  const total = data?.history.total ?? 0;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 sm:py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.02em]">Analytics</h1>
          <p className="mt-1.5 max-w-prose text-[15px] text-ink-soft">
            {data
              ? `Across ${plural(total, "request")} since the backend started. History is kept in memory and clears when the backend restarts.`
              : "Latency, cache, model, and context metrics across every recorded request."}
          </p>
        </div>
        <button
          type="button"
          onClick={analytics.reload}
          className="h-9 rounded-full border border-rule-strong bg-surface px-4 text-sm font-medium hover:border-ink-faint"
        >
          Refresh
        </button>
      </header>

      {analytics.error && (
        <div className="mt-6">
          <BackendNotice error={analytics.error} onRetry={analytics.reload} />
        </div>
      )}

      {data && total === 0 && (
        <div className="mt-10 rounded-lg border border-dashed border-rule-strong px-6 py-10 text-center">
          <p className="text-[15px] font-semibold">No requests yet.</p>
          <p className="mt-1 text-sm text-ink-soft">
            Send a message from the{" "}
            <Link href="/" className="underline decoration-rule-strong underline-offset-2 hover:text-ink">
              console
            </Link>{" "}
            and its metrics will show up here.
          </p>
        </div>
      )}

      {data && total > 0 && (
        <div className="mt-8 flex flex-col gap-12">
          <MetricGroups summary={data.summary} />

          <div className="grid gap-12 lg:grid-cols-[3fr_2fr]">
            <LatencyChart items={data.history.items} />
            <SourcesChart sources={data.summary.context.sources_used} />
          </div>

          <section>
            <h2 className="text-[15px] font-bold">Request history</h2>
            <p className="mt-1 mb-3 text-sm text-ink-soft">
              Select a request to replay it step by step.
            </p>
            <HistoryTable items={data.history.items} />
          </section>
        </div>
      )}
    </main>
  );
}
