import { COMPONENTS, type StatusKind, type StatusReading } from "@/lib/components";
import type { ComponentName } from "@/types/api";

/**
 * Status is carried by the fill, not the hue: the hue always says *which*
 * component, the fill says *what state*. Solid is live, half-filled is an
 * in-process stand-in (stub), hollow didn't run, and the red cross is a
 * failure. A stub must never look like a success, and "off" must never look
 * like "failed".
 */
export function StatusGlyph({
  component,
  kind,
  className = "size-2.5",
}: {
  component?: ComponentName;
  kind: StatusKind;
  className?: string;
}) {
  const color = component ? COMPONENTS[component].color : "var(--ink-soft)";

  if (kind === "unavailable") {
    return (
      <svg viewBox="0 0 10 10" aria-hidden className={`${className} shrink-0`}>
        <circle cx="5" cy="5" r="5" fill="var(--critical)" />
        <path d="M3.2 3.2l3.6 3.6M6.8 3.2l-3.6 3.6" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    );
  }

  if (kind === "off") {
    return (
      <span
        aria-hidden
        className={`${className} inline-block shrink-0 rounded-full border-[1.5px] border-rule-strong`}
      />
    );
  }

  return (
    <span
      aria-hidden
      className={`${className} inline-block shrink-0 rounded-full`}
      style={
        kind === "ok"
          ? { background: color }
          : { border: `1.5px solid ${color}`, background: `linear-gradient(90deg, ${color} 50%, transparent 50%)` }
      }
    />
  );
}

export function StatusBadge({
  component,
  reading,
  className = "",
}: {
  component?: ComponentName;
  reading: StatusReading;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm text-ink-soft ${className}`}>
      <StatusGlyph component={component} kind={reading.kind} />
      <span className={reading.kind === "unavailable" ? "text-critical-ink" : undefined}>
        {reading.label}
      </span>
    </span>
  );
}

/** A plain color key for a component, used beside text that names it. */
export function ChannelSwatch({
  component,
  className = "size-2.5 rounded-[3px]",
}: {
  component: ComponentName;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={`inline-block shrink-0 ${className}`}
      style={{ background: COMPONENTS[component].color }}
    />
  );
}
