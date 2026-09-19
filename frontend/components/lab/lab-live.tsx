"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { BackendNotice } from "@/components/backend-notice";
import { useConsole } from "@/components/chat/console-provider";
import { LAB, type LabComponent } from "@/components/lab/lab-content";
import { StatusBadge } from "@/components/status";
import { useBackendResource } from "@/hooks/use-backend-resource";
import { api } from "@/lib/api";
import { readStatus } from "@/lib/components";
import { formatClock, formatPercent, formatScore, formatUsd, plural } from "@/lib/format";
import type { AnalyticsSummary, ExecutionRecord, ExecutionSummary } from "@/types/api";

async function loadLab() {
  const [health, summary, history] = await Promise.all([api.health(), api.summary(), api.history()]);
  return { health, summary, history: history.items };
}

const live = (status: string) => status === "ok" || status === "stub";

// The most recent request this component ran in (for the cache, the most
// recent hit, since a miss contributes nothing).
function latestContribution(component: LabComponent, items: ExecutionSummary[]) {
  if (component === "cache") return items.find((item) => item.cache_hit);
  if (component === "memory") return items.find((item) => live(item.memory_status));
  return items.find((item) => live(item.retrieval_status));
}

export function LabLive({ component }: { component: LabComponent }) {
  const lab = useBackendResource("lab", loadLab);
  const { prepare } = useConsole();
  const router = useRouter();
  const entry = LAB[component];

  const health = lab.data?.health.components.find((item) => item.name === component);
  const latest = lab.data ? latestContribution(component, lab.data.history) : undefined;

  return (
    <section aria-label="Live from this backend" className="rounded-xl border border-rule bg-surface p-5 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[15px] font-bold">In this backend</h2>
        {health && <StatusBadge component={component} reading={readStatus(health.status)} />}
      </header>
      {health && <p className="mt-1 text-sm text-ink-soft">{health.detail}.</p>}

      {lab.error && (
        <div className="mt-4">
          <BackendNotice error={lab.error} onRetry={lab.reload} />
        </div>
      )}

      {lab.data && <UsageFigures component={component} summary={lab.data.summary} />}

      <div className="mt-5 border-t border-rule pt-5">
        <h3 className="text-sm font-semibold">{component === "cache" ? "Most recent hit" : "Most recent run"}</h3>
        {lab.data && !latest && (
          <p className="mt-1 text-sm text-ink-soft">
            {component === "cache"
              ? "No cache hits yet. Ask the same question twice to produce one."
              : "Not used by any request yet."}
          </p>
        )}
        {latest && <LatestContribution component={component} summary={latest} />}
      </div>

      <div className="mt-5 border-t border-rule pt-5">
        <h3 className="text-sm font-semibold">Try it</h3>
        <p className="mt-1 text-sm text-ink-soft">{entry.experiment.instructions}</p>
        <button
          type="button"
          onClick={() => {
            prepare(entry.experiment.message, entry.experiment.config);
            router.push("/");
          }}
          className="mt-3 h-9 rounded-full bg-ink px-4 text-sm font-semibold text-surface"
        >
          Load “{entry.experiment.message}” in the console
        </button>
      </div>
    </section>
  );
}

function UsageFigures({ component, summary }: { component: LabComponent; summary: AnalyticsSummary }) {
  const total = summary.llm.total_requests;
  const figures =
    component === "cache"
      ? [
          { label: "Hit rate", value: formatPercent(summary.cache.hit_rate) },
          { label: "Model calls avoided", value: String(summary.cache.llm_calls_avoided) },
          { label: "Saved (estimate)", value: `~${formatUsd(summary.llm.estimated_saved_usd)}` },
        ]
      : component === "memory"
        ? [
            { label: "Requests using memory", value: `${summary.context.memory_used} of ${total}` },
            {
              label: "Memories that reached the model",
              value: String(Object.keys(summary.context.sources_used).filter((s) => s.startsWith("memory")).length),
            },
          ]
        : [
            { label: "Requests using retrieval", value: `${summary.context.retrieval_used} of ${total}` },
            { label: "Average context size", value: `${Math.round(summary.context.average_context_tokens)} tokens` },
          ];

  return (
    <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
      {figures.map((figure) => (
        <div key={figure.label}>
          <dt className="text-xs text-ink-faint">{figure.label}</dt>
          <dd className="mt-0.5 text-xl font-bold tracking-[-0.01em]">{figure.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function LatestContribution({ component, summary }: { component: LabComponent; summary: ExecutionSummary }) {
  const record = useBackendResource(`lab-record:${summary.request_id}`, () => api.record(summary.request_id));

  return (
    <div className="mt-2 text-sm">
      <p>
        <span className="font-semibold">“{summary.message}”</span>{" "}
        <span className="text-ink-faint">at {formatClock(summary.started_at)}</span>
      </p>
      {record.data && <p className="mt-1 text-ink-soft">{describeContribution(component, record.data)}</p>}
      <Link
        href={`/analytics/${summary.request_id}`}
        className="mt-1.5 inline-block text-[13px] text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
      >
        Open replay
      </Link>
    </div>
  );
}

function describeContribution(component: LabComponent, record: ExecutionRecord): string {
  if (component === "cache") {
    const { cache } = record;
    return `Matched “${cache.matched_prompt}” at ${formatScore(cache.similarity ?? 1)} against a ${formatScore(
      cache.threshold ?? 0,
    )} threshold, so the model wasn't called.`;
  }
  if (component === "memory") {
    const used = record.context.included.filter((section) => section.origin === "memory");
    return `Found ${plural(record.memory.entries.length, "memory", "memories")}; ${
      used.length === 0 ? "none were relevant enough to use" : `used ${used.map((s) => s.name.replace("memory: ", "")).join(", ")}`
    }.`;
  }
  const rows = record.retrieval.sources.reduce((sum, source) => sum + source.records.length, 0);
  return `Queried ${plural(record.retrieval.sources.length, "source")} (${record.retrieval.sources
    .map((source) => source.tool)
    .join(", ")}) and returned ${plural(rows, "row")}.`;
}
