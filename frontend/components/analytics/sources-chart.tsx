import { COMPONENTS } from "@/lib/components";
import { formatCount } from "@/lib/format";

/** How often each context source reached the model, across all requests. */
export function SourcesChart({ sources }: { sources: Record<string, number> }) {
  const entries = Object.entries(sources);
  const most = Math.max(...entries.map(([, count]) => count), 1);

  return (
    <figure>
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <span>
          <span className="text-[15px] font-bold">Context that reached the model</span>{" "}
          <span className="text-sm text-ink-faint">requests per source</span>
        </span>
        <ul aria-label="Legend" className="flex gap-x-4 text-[13px] text-ink-soft">
          {(["retrieval", "memory"] as const).map((name) => (
            <li key={name} className="flex items-center gap-1.5">
              <span aria-hidden className="size-2.5 rounded-[3px]" style={{ background: COMPONENTS[name].color }} />
              {COMPONENTS[name].label}
            </li>
          ))}
        </ul>
      </figcaption>

      {entries.length === 0 ? (
        <p className="mt-4 text-sm text-ink-soft">No context has reached the model yet.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-2">
          {entries.map(([name, count]) => {
            const origin = name.startsWith("memory") ? "memory" : "retrieval";
            return (
              <li key={name} className="grid grid-cols-[minmax(0,11rem)_1fr] items-center gap-3 text-sm">
                <span className="truncate font-mono text-[13px] text-ink-soft" title={name}>
                  {name}
                </span>
                <span className="flex items-center gap-2">
                  <span
                    className="h-3.5 rounded-r-[4px]"
                    style={{ width: `${(count / most) * 85}%`, background: COMPONENTS[origin].color }}
                  />
                  <span className="text-[13px] tabular-nums">{formatCount(count)}</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </figure>
  );
}
