import { StatusGlyph } from "@/components/status";
import { COMPONENTS, isTurnedOff, readStatus } from "@/lib/components";
import { formatMs } from "@/lib/format";
import type { ComponentName, ExecutionRecord } from "@/types/api";

const STEPS: Record<string, { label: string; component?: ComponentName }> = {
  "cache lookup": { label: "Cache lookup", component: "cache" },
  memory: { label: "Memory", component: "memory" },
  "structured retrieval": { label: "Structured retrieval", component: "retrieval" },
  "context assembly": { label: "Context assembly" },
  llm: { label: "Model", component: "llm" },
  "cache store": { label: "Cache store", component: "cache" },
};

/**
 * The run replayed in order. The steps really are a sequence, so each bar
 * starts where the previous one ended: where the time went is read left to
 * right, the way the request spent it.
 */
export function StepWaterfall({ record }: { record: ExecutionRecord }) {
  const durations = record.steps.map((step) => step.duration_ms);
  const starts = durations.map((_, index) =>
    durations.slice(0, index).reduce((sum, duration) => sum + duration, 0),
  );
  const span = Math.max(
    durations.reduce((sum, duration) => sum + duration, 0),
    Number.EPSILON,
  );

  return (
    <ol className="divide-y divide-rule rounded-lg border border-rule bg-surface">
      {record.steps.map((step, index) => {
        const { label, component } = STEPS[step.name] ?? { label: step.name };
        const turnedOff = component ? isTurnedOff(record, component) : false;
        const reading = readStatus(step.status, turnedOff);
        const start = starts[index];

        return (
          <li
            key={step.name}
            className="grid grid-cols-[1.5rem_1fr_auto] items-start gap-x-3 gap-y-2 px-4 py-3 text-sm md:grid-cols-[1.5rem_minmax(0,13rem)_1fr_minmax(8rem,16rem)_4.5rem] md:items-center"
          >
            <span className="text-ink-faint tabular-nums">{index + 1}</span>
            <span className="flex items-center gap-2 font-semibold">
              <StatusGlyph component={component} kind={reading.kind} />
              {label}
              <span className="font-normal text-ink-faint">{reading.label}</span>
            </span>
            <span className="col-start-2 row-start-2 text-ink-soft md:col-start-auto md:row-start-auto">
              {step.detail}
            </span>
            <span
              aria-hidden
              className="relative col-span-2 col-start-2 row-start-3 h-2 rounded-full bg-surface-sunk md:col-span-1 md:col-start-auto md:row-start-auto"
            >
              {reading.kind !== "off" && (
                <span
                  className="absolute inset-y-0 rounded-full"
                  style={{
                    left: `${(start / span) * 100}%`,
                    width: `max(3px, ${(step.duration_ms / span) * 100}%)`,
                    background: component ? COMPONENTS[component].color : "var(--ink-soft)",
                  }}
                />
              )}
            </span>
            <span className="col-start-3 row-start-1 text-right text-ink-soft tabular-nums md:col-start-auto md:row-start-auto">
              {reading.kind === "off" ? "—" : formatMs(step.duration_ms)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
