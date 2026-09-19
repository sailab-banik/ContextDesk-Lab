import type { ReactNode } from "react";

import { ChannelSwatch, StatusBadge } from "@/components/status";
import type { StatusReading } from "@/lib/components";
import { formatMs } from "@/lib/format";
import type { ComponentName } from "@/types/api";

export function InspectorSection({
  title,
  component,
  status,
  durationMs,
  children,
}: {
  title: string;
  component?: ComponentName;
  status?: StatusReading;
  durationMs?: number;
  children: ReactNode;
}) {
  return (
    <section className="border-t border-rule py-5">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {component && <ChannelSwatch component={component} className="h-3.5 w-1 rounded-full" />}
        <h3 className="text-[15px] font-bold">{title}</h3>
        {status && <StatusBadge component={component} reading={status} />}
        {durationMs !== undefined && durationMs > 0 && (
          <span className="ml-auto text-sm text-ink-faint tabular-nums">{formatMs(durationMs)}</span>
        )}
      </header>
      <div className="mt-3">{children}</div>
    </section>
  );
}

/** Why a component produced nothing: it was turned off, skipped, or failed. */
export function NotRunNote({
  turnedOff,
  skippedReason,
  error,
  offText,
}: {
  turnedOff: boolean;
  skippedReason: string | null;
  error: string | null;
  offText: string;
}) {
  if (error) return <p className="text-sm text-critical-ink">{error}</p>;
  return (
    <p className="text-sm text-ink-soft">
      {turnedOff ? offText : `Skipped: ${skippedReason ?? "not needed for this request"}.`}
    </p>
  );
}
