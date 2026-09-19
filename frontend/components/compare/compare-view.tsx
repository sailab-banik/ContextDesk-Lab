"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { BackendNotice } from "@/components/backend-notice";
import { SCENARIOS } from "@/components/chat/scenarios";
import { StatusGlyph } from "@/components/status";
import { api, describeError } from "@/lib/api";
import { COMPONENTS, TOGGLEABLE, configLabel, isTurnedOff } from "@/lib/components";
import { formatCount, formatMs, formatScore, formatUsd, plural } from "@/lib/format";
import type { ComparisonResponse, ExecutionRecord } from "@/types/api";

type Row =
  | { label: string; kind: "text"; value: (record: ExecutionRecord) => string }
  | {
      label: string;
      kind: "number";
      value: (record: ExecutionRecord) => number;
      format: (value: number) => string;
    };

// The criteria PLAN.md compares on. Numeric rows get a bar scaled within the
// row, so the cost of each extra component reads at a glance.
const ROWS: Row[] = [
  { label: "Model called", kind: "text", value: (r) => (r.llm.called ? "Yes" : "No, served from cache") },
  {
    label: "Memory used",
    kind: "text",
    value: (r) =>
      isTurnedOff(r, "memory")
        ? "Off"
        : r.memory.status === "disabled"
          ? "Skipped"
          : `${r.memory.used_count} of ${plural(r.memory.entries.length, "memory", "memories")}`,
  },
  {
    label: "Structured context",
    kind: "text",
    value: (r) =>
      isTurnedOff(r, "retrieval")
        ? "Off"
        : r.retrieval.status === "disabled"
          ? "Skipped"
          : plural(r.retrieval.sources.length, "source"),
  },
  {
    label: "Cache",
    kind: "text",
    value: (r) =>
      isTurnedOff(r, "cache")
        ? "Off"
        : r.cache.hit
          ? `Hit at ${formatScore(r.cache.similarity ?? 1)}`
          : "Miss",
  },
  { label: "Total latency", kind: "number", value: (r) => r.total_duration_ms, format: formatMs },
  {
    label: "Context size",
    kind: "number",
    value: (r) => r.context.estimated_tokens,
    format: (v) => `${formatCount(v)} tokens`,
  },
  {
    label: "Cost (estimate)",
    kind: "number",
    value: (r) => r.llm.estimated_cost_usd,
    format: (v) => `~${formatUsd(v)}`,
  },
];

export function CompareView() {
  const [message, setMessage] = useState(SCENARIOS[1].message);
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(text: string) {
    const trimmed = text.trim();
    if (!trimmed || running) return;
    setMessage(trimmed);
    setRunning(true);
    setError(null);
    try {
      setResult(await api.compare(trimmed));
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 sm:py-10">
      <h1 className="text-3xl font-bold tracking-[-0.02em]">Compare configurations</h1>
      <p className="mt-1.5 max-w-prose text-[15px] text-ink-soft">
        Run one message four ways and see what each component adds and what it costs. More context
        isn&apos;t automatically better: a plan lookup doesn&apos;t need memory.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(message);
        }}
        className="mt-6 flex flex-col gap-3 sm:flex-row"
      >
        <label htmlFor="compare-message" className="sr-only">
          Message to compare
        </label>
        <input
          id="compare-message"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className="h-11 flex-1 rounded-lg border border-rule-strong bg-surface px-4 text-[15px] outline-none focus-visible:border-ink-soft focus-visible:shadow-[0_0_0_3px_color-mix(in_srgb,var(--llm)_18%,transparent)] focus-visible:outline-none"
        />
        <button
          type="submit"
          disabled={running || !message.trim()}
          className="h-11 rounded-lg bg-ink px-5 text-sm font-semibold text-surface disabled:opacity-40"
        >
          {running ? "Running 4 configurations…" : "Run comparison"}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-ink-faint">Try</span>
        {SCENARIOS.map((scenario) => (
          <button
            key={scenario.message}
            type="button"
            disabled={running}
            onClick={() => void run(scenario.message)}
            className="rounded-full border border-rule bg-surface px-3 py-1 text-ink-soft hover:border-rule-strong hover:text-ink disabled:opacity-40"
          >
            {scenario.message}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-6">
          <BackendNotice error={error} onRetry={() => void run(message)} />
        </div>
      )}

      {result && (
        <div className={`mt-8 transition-opacity ${running ? "opacity-45" : ""}`} aria-busy={running}>
          <ComparisonTable result={result} />
          <p className="mt-3 text-sm text-ink-faint">
            Comparison runs aren&apos;t written to conversation memory, so they don&apos;t change what
            the console remembers. Each run is still recorded in analytics.
          </p>
        </div>
      )}
    </main>
  );
}

function ComparisonTable({ result }: { result: ComparisonResponse }) {
  const records = result.runs.map((run) => run.execution);

  return (
    <div className="overflow-x-auto rounded-lg border border-rule bg-surface">
      <table className="w-full min-w-[52rem] table-fixed text-left text-sm">
        <caption className="sr-only">“{result.message}” across {result.runs.length} configurations</caption>
        <colgroup>
          <col className="w-44" />
        </colgroup>
        <thead>
          <tr className="border-b border-rule">
            <th scope="col" className="px-4 py-3 align-bottom text-[13px] font-medium text-ink-faint">
              Configuration
            </th>
            {result.runs.map((run) => (
              <th key={run.label} scope="col" className="px-4 py-3 align-bottom">
                <span className="flex gap-1.5" aria-hidden>
                  {TOGGLEABLE.map(({ name, key }) => (
                    <StatusGlyph key={name} component={name} kind={run.config[key] ? "ok" : "off"} />
                  ))}
                </span>
                <span className="mt-1.5 block text-[15px] font-bold">{configLabel(run.config)}</span>
                <span className="sr-only">
                  {TOGGLEABLE.map(({ name, key }) => `${COMPONENTS[name].label} ${run.config[key] ? "on" : "off"}`).join(", ")}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {ROWS.map((row) => (
            <tr key={row.label}>
              <th scope="row" className="px-4 py-3 font-medium text-ink-soft">
                {row.label}
              </th>
              {records.map((record) => (
                <td key={record.request_id} className="px-4 py-3">
                  {row.kind === "text" ? (
                    row.value(record)
                  ) : (
                    <NumberCell
                      value={row.value(record)}
                      max={Math.max(...records.map(row.value))}
                      format={row.format}
                    />
                  )}
                </td>
              ))}
            </tr>
          ))}
          <tr>
            <th scope="row" className="px-4 py-3 align-top font-medium text-ink-soft">
              Answer
            </th>
            {result.runs.map((run) => (
              <td key={run.execution.request_id} className="px-4 py-3 align-top">
                <Answer text={run.response}>
                  <Link
                    href={`/analytics/${run.execution.request_id}`}
                    className="text-[13px] text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
                  >
                    Open replay
                  </Link>
                </Answer>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function NumberCell({ value, max, format }: { value: number; max: number; format: (v: number) => string }) {
  return (
    <div>
      <span className="font-semibold tabular-nums">{format(value)}</span>
      <span aria-hidden className="mt-1.5 block h-1.5 rounded-full bg-surface-sunk">
        <span
          className="block h-full rounded-full bg-ink-soft"
          style={{ width: max > 0 ? `max(2px, ${(value / max) * 100}%)` : 0 }}
        />
      </span>
    </div>
  );
}

function Answer({ text, children }: { text: string; children: ReactNode }) {
  return (
    <>
      <details className="group">
        <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
          <span className="line-clamp-4 leading-5 whitespace-pre-wrap group-open:line-clamp-none">{text}</span>
          <span className="mt-1 block text-[13px] text-ink-faint group-open:hidden">Show full answer</span>
        </summary>
      </details>
      <span className="mt-2 block">{children}</span>
    </>
  );
}
