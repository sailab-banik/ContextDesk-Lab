import { COMPONENTS } from "@/lib/components";
import { formatScore } from "@/lib/format";
import type { ComponentName } from "@/types/api";

/**
 * A 0–1 score on a track, with the bar it was judged against. The threshold
 * tick is what turns a bare number into a decision the reader can check.
 */
export function ScoreMeter({
  value,
  threshold,
  component,
  label,
}: {
  value: number | null;
  threshold?: number | null;
  component: ComponentName;
  label: string;
}) {
  const passed = value != null && threshold != null && value >= threshold;
  return (
    <div
      role="img"
      aria-label={`${label} ${value == null ? "not scored" : formatScore(value)}${
        threshold != null ? `, threshold ${formatScore(threshold)}` : ""
      }`}
      className="relative h-6"
    >
      <span className="absolute inset-x-0 top-[9px] h-1.5 rounded-full bg-surface-sunk" />
      {value != null && (
        <span
          className="absolute top-[9px] left-0 h-1.5 rounded-full"
          style={{
            width: `${value * 100}%`,
            background: passed || threshold == null ? COMPONENTS[component].color : "var(--rule-strong)",
          }}
        />
      )}
      {threshold != null && (
        <span
          className="absolute top-1 h-4 w-0.5 -translate-x-1/2 rounded-full bg-ink"
          style={{ left: `${threshold * 100}%` }}
        />
      )}
    </div>
  );
}
