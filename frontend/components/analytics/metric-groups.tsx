import type { ReactNode } from "react";

import { ChannelSwatch } from "@/components/status";
import { formatCount, formatMs, formatPercent, formatUsd } from "@/lib/format";
import type { AnalyticsSummary, ComponentName } from "@/types/api";

/**
 * The four metric groups as a spec sheet: one column each, label on the left,
 * value on the right, so figures line up and compare down the column.
 */
export function MetricGroups({ summary }: { summary: AnalyticsSummary }) {
  const { latency, cache, llm, context } = summary;

  return (
    <div className="grid gap-x-10 gap-y-8 sm:grid-cols-2 xl:grid-cols-4">
      <Group title="Latency">
        <Row label="Average" value={formatMs(latency.average_ms)} />
        <Row label="P50" value={formatMs(latency.p50_ms)} />
        <Row label="P95" value={formatMs(latency.p95_ms)} />
        <Row label="Average model call" value={formatMs(latency.average_llm_ms)} />
        <Row label="Average cache hit" value={formatMs(latency.average_cache_hit_ms)} />
      </Group>

      <Group title="Cache" component="cache">
        <Row label="Hit rate" value={formatPercent(cache.hit_rate)}>
          <HitRateMeter rate={cache.hit_rate} />
        </Row>
        <Row label="Hits" value={formatCount(cache.hits)} />
        <Row label="Misses" value={formatCount(cache.misses)} />
        <Row label="Average lookup" value={formatMs(cache.average_lookup_ms)} />
        <Row label="Model calls avoided" value={formatCount(cache.llm_calls_avoided)} />
      </Group>

      <Group title="Model" component="llm">
        <Row label="Requests" value={formatCount(llm.total_requests)} />
        <Row label="Model calls" value={formatCount(llm.total_llm_calls)} />
        <Row label="Input tokens" value={formatCount(llm.input_tokens)} />
        <Row label="Output tokens" value={formatCount(llm.output_tokens)} />
        <Row label="Cost (estimate)" value={`~${formatUsd(llm.estimated_cost_usd)}`} />
        <Row label="Saved by cache (estimate)" value={`~${formatUsd(llm.estimated_saved_usd)}`} />
      </Group>

      <Group title="Context">
        <Row label="Used memory" value={`${formatCount(context.memory_used)} requests`} />
        <Row label="Used retrieval" value={`${formatCount(context.retrieval_used)} requests`} />
        <Row label="Consulted cache" value={`${formatCount(context.cache_used)} requests`} />
        <Row label="Average context" value={`${formatCount(context.average_context_tokens)} tokens`} />
      </Group>
    </div>
  );
}

function Group({
  title,
  component,
  children,
}: {
  title: string;
  component?: ComponentName;
  children: ReactNode;
}) {
  return (
    <section>
      <h2 className="flex items-center gap-2 border-b border-ink pb-2 text-[15px] font-bold">
        {component && <ChannelSwatch component={component} className="h-3.5 w-1 rounded-full" />}
        {title}
      </h2>
      <dl className="divide-y divide-rule">{children}</dl>
    </section>
  );
}

function Row({ label, value, children }: { label: string; value: string; children?: ReactNode }) {
  return (
    <div className="py-2">
      <div className="flex items-baseline justify-between gap-4">
        <dt className="text-sm text-ink-soft">{label}</dt>
        <dd className="text-[15px] font-semibold tabular-nums">{value}</dd>
      </div>
      {children}
    </div>
  );
}

function HitRateMeter({ rate }: { rate: number }) {
  return (
    <div aria-hidden className="mt-1.5 h-1.5 rounded-full bg-cache/20">
      <div className="h-full rounded-full bg-cache" style={{ width: `${rate * 100}%` }} />
    </div>
  );
}
