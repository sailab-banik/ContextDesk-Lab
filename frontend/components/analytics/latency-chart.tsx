import Link from "next/link";

import { COMPONENTS } from "@/lib/components";
import { formatClock, formatMs } from "@/lib/format";
import type { ExecutionSummary } from "@/types/api";

type Path = "llm" | "cache" | "none";

const PATHS: Record<Path, { label: string; color: string }> = {
  llm: { label: "Model called", color: COMPONENTS.llm.color },
  cache: { label: "Served from cache", color: COMPONENTS.cache.color },
  none: { label: "No answer produced", color: "var(--ink-faint)" },
};

function pathOf(item: ExecutionSummary): Path {
  if (item.cache_hit) return "cache";
  return item.llm_called ? "llm" : "none";
}

/** Rounds an axis maximum up to 1, 2, or 5 times a power of ten. */
function niceCeiling(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((candidate) => candidate * magnitude >= value) ?? 10;
  return step * magnitude;
}

/**
 * One column per request, oldest to newest, colored by what produced the
 * answer. It exists to make one comparison obvious: how much faster a cache
 * hit is than a model call.
 */
export function LatencyChart({ items }: { items: ExecutionSummary[] }) {
  const requests = [...items].reverse().slice(-60);
  const ceiling = niceCeiling(Math.max(...requests.map((item) => item.total_duration_ms)));
  const present = (Object.keys(PATHS) as Path[]).filter((path) =>
    requests.some((item) => pathOf(item) === path),
  );

  return (
    <figure>
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <span>
          <span className="text-[15px] font-bold">Latency per request</span>{" "}
          <span className="text-sm text-ink-faint">oldest to newest</span>
        </span>
        <ul aria-label="Legend" className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-ink-soft">
          {present.map((path) => (
            <li key={path} className="flex items-center gap-1.5">
              <span aria-hidden className="size-2.5 rounded-[3px]" style={{ background: PATHS[path].color }} />
              {PATHS[path].label}
            </li>
          ))}
        </ul>
      </figcaption>

      <div className="mt-4 grid grid-cols-[auto_1fr] gap-x-3">
        <div aria-hidden className="relative h-44 text-right text-xs text-ink-faint tabular-nums">
          <span className="absolute top-0 right-0 -translate-y-1/2">{formatMs(ceiling)}</span>
          <span className="absolute top-1/2 right-0 -translate-y-1/2">{formatMs(ceiling / 2)}</span>
          <span className="absolute right-0 bottom-0 translate-y-1/2">0</span>
          <span className="invisible">{formatMs(ceiling)}</span>
        </div>

        <div className="relative h-44">
          <span aria-hidden className="absolute inset-x-0 top-0 h-px bg-rule" />
          <span aria-hidden className="absolute inset-x-0 top-1/2 h-px bg-rule" />
          <span aria-hidden className="absolute inset-x-0 bottom-0 h-px bg-rule-strong" />

          <ol className="absolute inset-0 flex items-end gap-[2px]">
            {requests.map((item, index) => {
              const path = pathOf(item);
              const alignRight = index > requests.length / 2;
              return (
                <li key={item.request_id} className="group relative flex h-full max-w-6 flex-1 items-end">
                  <Link
                    href={`/analytics/${item.request_id}`}
                    aria-label={`${item.message}: ${formatMs(item.total_duration_ms)}, ${PATHS[path].label.toLowerCase()}. Open replay.`}
                    className="flex h-full w-full items-end rounded-t-[4px]"
                  >
                    <span
                      className="block w-full rounded-t-[4px] transition-opacity group-hover:opacity-80"
                      style={{
                        height: `max(2px, ${(item.total_duration_ms / ceiling) * 100}%)`,
                        background: PATHS[path].color,
                      }}
                    />
                  </Link>
                  <span
                    role="tooltip"
                    className={`pointer-events-none absolute bottom-full z-10 mb-2 hidden w-60 max-w-[calc(100vw-2rem)] rounded-lg border border-rule bg-surface px-3 py-2 text-[13px] shadow-lg shadow-black/5 group-focus-within:block group-hover:block ${
                      alignRight ? "right-0" : "left-0"
                    }`}
                  >
                    <span className="line-clamp-2 font-semibold">{item.message}</span>
                    <span className="mt-1 flex justify-between text-ink-soft">
                      <span>{PATHS[path].label}</span>
                      <span className="tabular-nums">{formatMs(item.total_duration_ms)}</span>
                    </span>
                    <span className="block text-xs text-ink-faint">{formatClock(item.started_at)}</span>
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </figure>
  );
}
