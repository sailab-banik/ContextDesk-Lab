import { ChannelSwatch } from "@/components/status";
import { COMPONENTS, EXCLUSION_REASONS, originComponent } from "@/lib/components";
import { formatCount } from "@/lib/format";
import type { ContextSummary } from "@/types/api";

/**
 * What reached the model, and what was available but left out. The system
 * selects context rather than sending everything; this is where that
 * selection becomes visible.
 */
export function ContextBudget({ context, cacheHit }: { context: ContextSummary; cacheHit: boolean }) {
  const { included, excluded, budget_tokens: budget, estimated_tokens: used } = context;
  const ghosts = excluded.filter((item) => item.estimated_tokens > 0);
  const ghostTokens = ghosts.reduce((sum, item) => sum + item.estimated_tokens, 0);
  // Scale to the budget, or past it when the left-out context would overflow,
  // so every segment keeps its true proportion.
  const scale = Math.max(budget, used + ghostTokens, 1);

  const byOrigin = (origin: "memory" | "retrieval") =>
    included
      .filter((section) => originComponent(section.origin) === origin)
      .reduce((sum, section) => sum + section.estimated_tokens, 0);

  return (
    <section className="py-5">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="text-[15px] font-bold">What reached the model</h3>
        <span className="text-sm text-ink-soft tabular-nums">
          {formatCount(used)} of {formatCount(budget)} token budget
        </span>
      </header>

      {included.length === 0 ? (
        <p className="mt-3 text-sm text-ink-soft">
          {cacheHit
            ? "No context was assembled: the answer came straight from the cache, so the model never ran."
            : "No context reached the model. It answered from the message alone."}
        </p>
      ) : (
        <>
          <div
            role="img"
            aria-label={`${formatCount(used)} of ${formatCount(budget)} tokens used by ${included.length} context sections; ${ghosts.length} more sections left out.`}
            className="mt-3 flex h-3 gap-[2px] rounded-[4px] bg-surface-sunk"
          >
            {included.map((section) => (
              <span
                key={section.name}
                title={`${section.name}: ${section.estimated_tokens} tokens`}
                className="h-full first:rounded-l-[4px]"
                style={{
                  width: `${(section.estimated_tokens / scale) * 100}%`,
                  background: COMPONENTS[originComponent(section.origin)].color,
                }}
              />
            ))}
            {ghosts.map((item) => (
              <span
                key={item.name}
                title={`Left out: ${item.name}, ${item.estimated_tokens} tokens`}
                className="h-full border border-dashed"
                style={{
                  width: `${(item.estimated_tokens / scale) * 100}%`,
                  borderColor: COMPONENTS[originComponent(item.origin)].color,
                }}
              />
            ))}
          </div>

          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-ink-soft" aria-label="Legend">
            {(["retrieval", "memory"] as const).map((origin) => (
              <li key={origin} className="flex items-center gap-1.5">
                <ChannelSwatch component={origin} className="size-2.5 rounded-[3px]" />
                {COMPONENTS[origin].label}
                <span className="tabular-nums">{formatCount(byOrigin(origin))}</span>
              </li>
            ))}
            {ghosts.length > 0 && (
              <li className="flex items-center gap-1.5">
                <span aria-hidden className="size-2.5 rounded-[3px] border border-dashed border-ink-faint" />
                Left out
                <span className="tabular-nums">{formatCount(ghostTokens)}</span>
              </li>
            )}
          </ul>

          <ul className="mt-4 divide-y divide-rule rounded-lg border border-rule">
            {included.map((section) => (
              <li key={section.name}>
                <details className="group">
                  <summary className="flex cursor-pointer list-none items-center gap-2.5 px-3 py-2 text-sm hover:bg-surface-sunk [&::-webkit-details-marker]:hidden">
                    <ChannelSwatch component={originComponent(section.origin)} />
                    <span className="min-w-0 truncate font-mono text-[13px]">{section.name}</span>
                    <span className="ml-auto text-ink-faint tabular-nums">
                      {formatCount(section.estimated_tokens)} tokens
                    </span>
                    <Chevron />
                  </summary>
                  <pre className="overflow-x-auto border-t border-rule bg-surface-sunk px-3 py-2.5 font-mono text-xs leading-5 whitespace-pre-wrap text-ink-soft">
                    {section.content}
                  </pre>
                </details>
              </li>
            ))}
          </ul>
        </>
      )}

      {excluded.length > 0 && (
        <div className="mt-5">
          <h4 className="text-sm font-semibold">
            Left out <span className="font-normal text-ink-faint">{excluded.length}</span>
          </h4>
          <ul className="mt-2 flex flex-col gap-1.5">
            {excluded.map((item) => (
              <li
                key={item.name}
                className="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-2.5 text-sm sm:grid-cols-[auto_minmax(0,18rem)_1fr]"
              >
                <span
                  aria-hidden
                  className="size-2.5 translate-y-px rounded-[3px] border border-dashed"
                  style={{ borderColor: COMPONENTS[originComponent(item.origin)].color }}
                />
                <span className="truncate font-mono text-[13px] text-ink-soft">{item.name}</span>
                <span className="col-start-2 text-ink-soft sm:col-start-3">
                  {EXCLUSION_REASONS[item.reason]}
                  {item.detail && <span className="text-ink-faint">, {item.detail}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function Chevron() {
  return (
    <svg
      viewBox="0 0 12 12"
      aria-hidden
      className="size-3 shrink-0 text-ink-faint transition-transform group-open:rotate-90"
    >
      <path d="M4.5 2.5 8 6l-3.5 3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
