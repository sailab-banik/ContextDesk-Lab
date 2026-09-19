import Link from "next/link";

import { StatusGlyph } from "@/components/status";
import { COMPONENTS, readStatus } from "@/lib/components";
import { formatClock, formatCount, formatMs } from "@/lib/format";
import type { ExecutionSummary } from "@/types/api";

// The summary row carries statuses but not the config, so "turned off" is read
// from the config label, which lists exactly the components that were enabled.
function summaryStatus(item: ExecutionSummary, name: "memory" | "retrieval" | "cache") {
  return readStatus(item[`${name}_status`], !item.config_label.includes(name));
}

export function HistoryTable({ items }: { items: ExecutionSummary[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-rule bg-surface">
      <table className="w-full min-w-[46rem] text-left text-sm">
        <thead className="border-b border-rule text-[13px] text-ink-faint">
          <tr>
            <th scope="col" className="px-4 py-2.5 font-medium">Time</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Message</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Memory, retrieval, cache</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Cache</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Model</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Context</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Latency</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule">
          {items.map((item) => (
            <tr key={item.request_id} className="relative hover:bg-surface-sunk">
              <td className="px-4 py-2.5 text-ink-soft tabular-nums">{formatClock(item.started_at)}</td>
              <td className="max-w-[20rem] px-4 py-2.5">
                {/* The link stretches over the whole row, so any cell opens the replay. */}
                <Link
                  href={`/analytics/${item.request_id}`}
                  className="block truncate font-semibold after:absolute after:inset-0 after:content-['']"
                >
                  {item.message}
                </Link>
              </td>
              <td className="px-4 py-2.5">
                <span className="flex items-center gap-2.5">
                  {(["memory", "retrieval", "cache"] as const).map((name) => {
                    const reading = summaryStatus(item, name);
                    return (
                      <span key={name} title={`${COMPONENTS[name].label}: ${reading.label}`} className="flex">
                        <StatusGlyph component={name} kind={reading.kind} />
                        <span className="sr-only">
                          {COMPONENTS[name].label} {reading.label}
                        </span>
                      </span>
                    );
                  })}
                </span>
              </td>
              <td className="px-4 py-2.5 text-ink-soft">
                {item.cache_status === "disabled" ? "Off" : item.cache_hit ? "Hit" : "Miss"}
              </td>
              <td className="px-4 py-2.5 text-ink-soft">{item.llm_called ? "Called" : "Not called"}</td>
              <td className="px-4 py-2.5 text-right text-ink-soft tabular-nums">
                {formatCount(item.context_tokens)} tokens
              </td>
              <td className="px-4 py-2.5 text-right font-semibold tabular-nums">
                {formatMs(item.total_duration_ms)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
