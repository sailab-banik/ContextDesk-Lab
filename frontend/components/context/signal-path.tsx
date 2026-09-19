import { StatusGlyph } from "@/components/status";
import { COMPONENTS, isTurnedOff, readStatus, type StatusReading } from "@/lib/components";
import { formatCount, formatMs, formatScore } from "@/lib/format";
import type { ComponentName, ExecutionRecord } from "@/types/api";

interface Station {
  step: string;
  label: string;
  component?: ComponentName;
  /** Shown before any message is sent, so the pipeline explains itself. */
  purpose: string;
  result: (record: ExecutionRecord) => string;
}

// Fixed, in the order the chat service runs them. A request that ends early
// (a cache hit) still shows every station, so what it skipped is visible.
const STATIONS: Station[] = [
  {
    step: "cache lookup",
    label: "Cache lookup",
    component: "cache",
    purpose: "Looks for an earlier question that means the same thing.",
    result: ({ cache }) =>
      cache.hit
        ? `Hit at ${formatScore(cache.similarity ?? 1)}`
        : cache.similarity != null
          ? `Miss at ${formatScore(cache.similarity)}`
          : "Miss",
  },
  {
    step: "memory",
    label: "Memory",
    component: "memory",
    purpose: "Recalls what this customer reported before.",
    result: ({ memory }) => `${memory.used_count} of ${memory.entries.length} used`,
  },
  {
    step: "structured retrieval",
    label: "Retrieval",
    component: "retrieval",
    purpose: "Fetches plan, usage, tickets, and incidents.",
    result: ({ retrieval }) => {
      const records = retrieval.sources.reduce((sum, source) => sum + source.records.length, 0);
      return `${retrieval.sources.length} sources, ${records} rows`;
    },
  },
  {
    step: "context assembly",
    label: "Assembly",
    purpose: "Keeps what fits the budget and is relevant.",
    result: ({ context }) => `${formatCount(context.estimated_tokens)} tokens`,
  },
  {
    step: "llm",
    label: "Model",
    component: "llm",
    purpose: "Answers from the message and the context.",
    result: ({ llm }) => `${formatCount(llm.input_tokens)} in, ${formatCount(llm.output_tokens)} out`,
  },
  {
    step: "cache store",
    label: "Cache store",
    component: "cache",
    purpose: "Saves the answer for similar questions.",
    result: ({ cache }) => (cache.stored ? "Stored" : "Not stored"),
  },
];

const NOT_RUN: StatusReading = { kind: "off", label: "Not run" };
const OFF: StatusReading = { kind: "off", label: "Off" };

export function SignalPath({ record }: { record: ExecutionRecord | undefined }) {
  const steps = record?.steps ?? [];
  const slowest = Math.max(...steps.map((step) => step.duration_ms), 0);

  return (
    <div className="@container">
      <ol
        // Keyed by request so the lighting sequence replays for each new record.
        key={record?.request_id ?? "idle"}
        className="relative grid grid-cols-2 gap-x-4 gap-y-5 @md:grid-cols-3 @2xl:grid-cols-6 @2xl:gap-x-3"
      >
        <span
          aria-hidden
          className="absolute top-[7px] right-[calc(100%/6-7px)] left-[7px] hidden h-px bg-rule-strong @2xl:block"
        />
        {STATIONS.map((station, index) => {
          const step = steps.find((candidate) => candidate.name === station.step);
          const turnedOff =
            record !== undefined && station.component !== undefined && isTurnedOff(record, station.component);
          const reading = step ? readStatus(step.status, turnedOff) : turnedOff ? OFF : NOT_RUN;
          const ran = step !== undefined && reading.kind !== "off";
          const share = ran && slowest > 0 ? step.duration_ms / slowest : 0;

          return (
            <li key={station.step} className="relative flex flex-col" title={step?.detail}>
              <span className="flex h-3.5 items-center">
                <span
                  className={`rounded-full bg-surface p-[2px] ${record ? "station-light" : ""}`}
                  style={{ ["--step" as string]: index }}
                >
                  {station.component ? (
                    <StatusGlyph component={station.component} kind={reading.kind} className="size-3" />
                  ) : (
                    <StatusGlyph kind={ran ? "ok" : "off"} className="size-3" />
                  )}
                </span>
              </span>

              <span className="mt-2 text-sm font-semibold">{station.label}</span>
              <span className="text-[13px] leading-5 text-ink-soft">
                {!record ? station.purpose : ran ? station.result(record) : reading.label}
              </span>

              {record && (
                <span className="mt-1.5 flex items-center gap-2">
                  <span className="h-[3px] flex-1 rounded-full bg-surface-sunk">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: ran ? `max(3px, ${share * 100}%)` : 0,
                        background: station.component
                          ? COMPONENTS[station.component].color
                          : "var(--ink-soft)",
                      }}
                    />
                  </span>
                  <span className="text-xs text-ink-faint tabular-nums">
                    {ran ? formatMs(step.duration_ms) : "—"}
                  </span>
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
