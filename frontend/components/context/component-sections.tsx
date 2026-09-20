"use client";

import type { ReactNode } from "react";

import { Chevron } from "@/components/context/context-budget";
import { InspectorSection, NotRunNote } from "@/components/context/inspector-section";
import { ScoreMeter } from "@/components/context/score-meter";
import { StatusGlyph } from "@/components/status";
import { useBackendResource } from "@/hooks/use-backend-resource";
import { api } from "@/lib/api";
import { componentStatus, isTurnedOff } from "@/lib/components";
import { formatCount, formatMs, formatScore, formatUsd, plural } from "@/lib/format";
import type { ExecutionRecord, RetrievedSource } from "@/types/api";

export function CacheSection({ record }: { record: ExecutionRecord }) {
  const { cache } = record;
  const ran = cache.status === "ok" || cache.status === "stub";

  return (
    <InspectorSection
      title="Semantic cache"
      component="cache"
      status={componentStatus(record, "cache")}
      durationMs={cache.duration_ms}
    >
      {!ran ? (
        <NotRunNote
          turnedOff={isTurnedOff(record, "cache")}
          skippedReason={cache.skipped_reason}
          error={cache.error}
          offText="Cache was off for this request, so every step below ran."
        />
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm">
            <span className="font-semibold">{cache.hit ? "Hit." : "Miss."}</span>{" "}
            <span className="text-ink-soft">
              {cache.similarity == null
                ? "No cached prompt scored high enough to be worth reporting."
                : `Closest cached prompt scored ${formatScore(cache.similarity)}, ${
                    cache.hit ? "at or above" : "below"
                  } the ${formatScore(cache.threshold ?? 0)} threshold.`}
            </span>
          </p>

          <div className="max-w-md">
            <ScoreMeter
              value={cache.similarity}
              threshold={cache.threshold}
              component="cache"
              label="Similarity"
            />
            <div className="flex justify-between text-xs text-ink-faint tabular-nums">
              <span>0</span>
              <span>Threshold {formatScore(cache.threshold ?? 0)}</span>
              <span>1</span>
            </div>
          </div>

          {cache.matched_prompt && (
            <blockquote className="border-l-2 border-cache pl-3 text-sm">
              <span className="text-ink-faint">
                {cache.hit ? "Matched prompt" : "Closest prompt, not used"}
              </span>
              <span className="block text-ink">“{cache.matched_prompt}”</span>
            </blockquote>
          )}

          {cache.hit && <CacheSavings requestId={record.request_id} />}
          {cache.stored && (
            <p className="text-sm text-ink-soft">This answer was stored for future lookups.</p>
          )}
          <p className="text-xs text-ink-faint">
            The lookup searches wider than this threshold and the hit is decided here, so a miss
            still reports how close it came.
          </p>
        </div>
      )}
    </InspectorSection>
  );
}

/**
 * What skipping the model saved can't be measured, only estimated. This uses
 * the backend's own estimate (each avoided call priced at the average of the
 * calls that did happen), so the inspector and analytics always agree.
 */
function CacheSavings({ requestId }: { requestId: string }) {
  const summary = useBackendResource(`savings:${requestId}`, api.summary);
  if (!summary.data) return null;
  const { latency, llm, cache } = summary.data;
  if (llm.total_llm_calls === 0 || cache.llm_calls_avoided === 0) {
    return (
      <p className="text-sm text-ink-soft">
        The model wasn&apos;t called. There are no model calls yet to estimate the saving from.
      </p>
    );
  }
  return (
    <p className="text-sm text-ink-soft">
      The model wasn&apos;t called. At the average of {plural(llm.total_llm_calls, "model call")} so
      far, that saved about{" "}
      <span className="text-ink tabular-nums">{formatMs(latency.average_llm_ms)}</span> of model time{" "}
      and <span className="text-ink tabular-nums">~{formatUsd(llm.estimated_saved_usd / cache.llm_calls_avoided)}</span>{" "}
      (estimate).
    </p>
  );
}

export function MemorySection({ record }: { record: ExecutionRecord }) {
  const { memory, context } = record;
  const used = new Set(context.included.map((section) => section.name));

  return (
    <InspectorSection
      title="Memory"
      component="memory"
      status={componentStatus(record, "memory")}
      durationMs={memory.duration_ms}
    >
      {memory.status === "disabled" || memory.status === "unavailable" ? (
        <NotRunNote
          turnedOff={isTurnedOff(record, "memory")}
          skippedReason={memory.skipped_reason}
          error={memory.error}
          offText="Memory was off, so the model had no history of earlier conversations."
        />
      ) : memory.entries.length === 0 ? (
        <p className="text-sm text-ink-soft">No memories were found for this customer.</p>
      ) : (
        <>
          <p className="text-sm text-ink-soft">
            {memory.used_count} of {plural(memory.entries.length, "memory", "memories")} relevant
            enough to use.
          </p>
          <ul className="mt-3 flex flex-col gap-3">
            {memory.entries.map((entry) => {
              const isUsed = used.has(`memory: ${entry.id}`);
              return (
                <li key={entry.id} className="grid grid-cols-[4.5rem_1fr] gap-x-3 text-sm">
                  <div className="pt-0.5">
                    <ScoreMeter value={entry.relevance} component="memory" label="Relevance" />
                    <p className="-mt-1 text-xs text-ink-faint tabular-nums">
                      {entry.relevance == null ? "Unscored" : formatScore(entry.relevance)}
                    </p>
                  </div>
                  <div className={isUsed ? "" : "text-ink-soft"}>
                    <p className="flex items-center gap-1.5 text-xs text-ink-faint">
                      <StatusGlyph component="memory" kind={isUsed ? "ok" : "off"} className="size-2" />
                      {isUsed ? "Used" : "Left out"}
                      <span className="font-mono">{entry.id}</span>
                    </p>
                    <p className="mt-0.5 leading-5">{entry.text}</p>
                    {entry.topics.length > 0 && (
                      <p className="mt-1 flex flex-wrap gap-1">
                        {entry.topics.map((topic) => (
                          <span
                            key={topic}
                            className="rounded bg-surface-sunk px-1.5 py-px text-xs text-ink-soft"
                          >
                            {topic}
                          </span>
                        ))}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </InspectorSection>
  );
}

export function RetrievalSection({ record }: { record: ExecutionRecord }) {
  const { retrieval } = record;
  const rows = retrieval.sources.reduce((sum, source) => sum + source.records.length, 0);

  return (
    <InspectorSection
      title="Structured context"
      component="retrieval"
      status={componentStatus(record, "retrieval")}
      durationMs={retrieval.duration_ms}
    >
      {retrieval.status === "disabled" || retrieval.status === "unavailable" ? (
        <NotRunNote
          turnedOff={isTurnedOff(record, "retrieval")}
          skippedReason={retrieval.skipped_reason}
          error={retrieval.error}
          offText="Retrieval was off, so the model saw no account data: no plan, usage, tickets, or incidents."
        />
      ) : (
        <>
          <p className="text-sm text-ink-soft">
            {plural(retrieval.sources.length, "source")} queried, {plural(rows, "row")} returned.
          </p>
          <ul className="mt-3 divide-y divide-rule rounded-lg border border-rule">
            {retrieval.sources.map((source) => (
              <li key={source.name}>
                <SourceRow source={source} />
              </li>
            ))}
          </ul>
        </>
      )}
    </InspectorSection>
  );
}

function SourceRow({ source }: { source: RetrievedSource }) {
  const args = Object.entries(source.arguments)
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");

  return (
    <details className="group">
      <summary className="grid cursor-pointer list-none grid-cols-[1fr_auto_auto] items-center gap-x-3 px-3 py-2 text-sm hover:bg-surface-sunk [&::-webkit-details-marker]:hidden">
        <span className="min-w-0">
          <span className="flex items-center gap-2 font-semibold">
            {source.status === "unavailable" && <StatusGlyph kind="unavailable" />}
            {source.name.replaceAll("_", " ")}
          </span>
          <span className="block truncate font-mono text-xs text-ink-faint">
            {source.tool}({args})
          </span>
        </span>
        <span className="text-ink-soft tabular-nums">{plural(source.records.length, "row")}</span>
        <Chevron />
      </summary>
      <div className="border-t border-rule bg-surface-sunk px-3 py-2.5">
        {source.error && <p className="mb-2 text-sm text-critical-ink">{source.error}</p>}
        {source.records.length === 0 ? (
          <p className="text-sm text-ink-soft">No rows matched.</p>
        ) : (
          <div className="flex flex-col gap-2.5">
            {source.records.map((row, index) => (
              <dl
                key={String(row.id ?? index)}
                className="grid grid-cols-[minmax(0,9rem)_1fr] gap-x-3 text-xs leading-5"
              >
                {Object.entries(row).map(([field, value]) => (
                  <div key={field} className="contents">
                    <dt className="truncate font-mono text-ink-faint">{field}</dt>
                    <dd className="min-w-0 wrap-break-word text-ink">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

export function ModelSection({ record }: { record: ExecutionRecord }) {
  const { llm } = record;

  return (
    <InspectorSection
      title="Model"
      component="llm"
      status={componentStatus(record, "llm")}
      durationMs={llm.duration_ms}
    >
      {!llm.called ? (
        <NotRunNote
          turnedOff={isTurnedOff(record, "llm")}
          skippedReason={llm.skipped_reason}
          error={llm.error}
          offText="The model was not called."
        />
      ) : (
        <>
          {llm.error && <p className="mb-3 text-sm text-critical-ink">{llm.error}</p>}
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
            <Figure label="Model" value={<span className="font-mono text-[13px]">{llm.model}</span>} />
            <Figure label="Input tokens" value={formatCount(llm.input_tokens)} />
            <Figure label="Output tokens" value={formatCount(llm.output_tokens)} />
            <Figure label="Cost (estimate)" value={`~${formatUsd(llm.estimated_cost_usd)}`} />
          </dl>
        </>
      )}
    </InspectorSection>
  );
}

function Figure({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-faint">{label}</dt>
      <dd className="mt-0.5 truncate font-semibold">{value}</dd>
    </div>
  );
}
