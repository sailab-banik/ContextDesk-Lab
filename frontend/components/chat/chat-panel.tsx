"use client";

import { useEffect, useRef } from "react";

import { Composer } from "@/components/chat/composer";
import { useConsole, type ChatTurn } from "@/components/chat/console-provider";
import { SCENARIOS } from "@/components/chat/scenarios";
import { StatusGlyph } from "@/components/status";
import { COMPONENTS, TOGGLEABLE, componentStatus, isTurnedOff } from "@/lib/components";
import { formatCount, formatMs } from "@/lib/format";
import type { ExecutionRecord } from "@/types/api";

export function ChatPanel() {
  const { turns, newConversation, pending } = useConsole();
  const endRef = useRef<HTMLDivElement>(null);
  const lastTurn = turns.at(-1);

  // Follow the conversation as it grows, including when a pending answer lands.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [turns.length, lastTurn?.status]);

  return (
    <section aria-label="Support chat" className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 pt-4 pb-3 whitespace-nowrap sm:px-6">
        <h1 className="text-[15px] font-bold">Support chat</h1>
        <span className="text-sm text-ink-faint">
          as customer <span className="font-mono text-[13px]">CUST-1001</span>
        </span>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={newConversation}
            disabled={pending}
            className="ml-auto rounded-md px-2 py-1 text-sm text-ink-soft hover:bg-surface-sunk hover:text-ink disabled:opacity-40"
          >
            New conversation
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6">
        {turns.length === 0 ? (
          <EmptyConversation />
        ) : (
          <ol className="flex flex-col gap-7 pt-2 pb-6">
            {turns.map((turn) => (
              <Turn key={turn.id} turn={turn} />
            ))}
          </ol>
        )}
        <div ref={endRef} />
      </div>

      <div className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6">
        <Composer />
      </div>
    </section>
  );
}

function EmptyConversation() {
  const { send, pending } = useConsole();

  return (
    <div className="flex h-full flex-col justify-end gap-6 pb-6">
      <div className="max-w-md">
        <h2 className="text-2xl leading-tight font-bold tracking-[-0.015em] text-balance">
          Ask the support assistant something.
        </h2>
        <p className="mt-2 text-[15px] leading-6 text-ink-soft">
          Every answer arrives with its execution record: where the context came from, what was
          left out, and what each step cost.
        </p>
      </div>

      <ul className="flex flex-col gap-2">
        {SCENARIOS.map((scenario) => (
          <li key={scenario.message}>
            <button
              type="button"
              disabled={pending}
              onClick={() => send(scenario.message)}
              className="group w-full rounded-lg border border-rule bg-surface px-4 py-3 text-left transition-colors hover:border-rule-strong"
            >
              <span className="block text-[15px] font-semibold">{scenario.message}</span>
              <span className="mt-0.5 block text-sm text-ink-soft">{scenario.note}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Turn({ turn }: { turn: ChatTurn }) {
  const { selectedTurn, selectTurn, retry, pending } = useConsole();
  const selected = selectedTurn?.id === turn.id;
  const offComponents = TOGGLEABLE.filter(({ key }) => !turn.config[key]).map(
    ({ name }) => COMPONENTS[name].label,
  );

  return (
    <li className="flex flex-col gap-3">
      <div className="flex flex-col items-end gap-1">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[15px] leading-6 text-surface">
          {turn.message}
        </p>
        {offComponents.length > 0 && (
          <p className="text-xs text-ink-faint">Sent without {offComponents.join(", ").toLowerCase()}</p>
        )}
      </div>

      {turn.status === "pending" && (
        <p role="status" className="flex items-center gap-2 text-sm text-ink-soft">
          <span className="flex gap-1" aria-hidden>
            {(["cache", "memory", "retrieval", "llm"] as const).map((name, index) => (
              <span
                key={name}
                className="working-dot size-1.5 rounded-full"
                style={{ background: COMPONENTS[name].color, ["--step" as string]: index }}
              />
            ))}
          </span>
          Running the pipeline…
        </p>
      )}

      {turn.status === "error" && (
        <div role="alert" className="rounded-lg border border-critical/40 px-4 py-3 text-sm">
          <p className="flex items-start gap-2 text-critical-ink">
            <StatusGlyph kind="unavailable" className="mt-1 size-2.5" />
            {turn.error}
          </p>
          <button
            type="button"
            onClick={() => retry(turn.id)}
            disabled={pending}
            className="mt-2 rounded-md px-2 py-1 text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink disabled:opacity-40"
          >
            Try again
          </button>
        </div>
      )}

      {turn.status === "done" && turn.record && (
        <div
          className={`-ml-3 border-l-2 pl-3 transition-colors ${selected ? "border-ink" : "border-transparent"}`}
        >
          <p className="max-w-prose text-[15px] leading-6 whitespace-pre-wrap">{turn.response}</p>
          <button
            type="button"
            onClick={() => selectTurn(turn.id)}
            aria-pressed={selected}
            aria-label="Show this answer's execution record in the inspector"
            className={`mt-2.5 flex flex-wrap items-center gap-x-3.5 gap-y-1 rounded-md py-1 text-[13px] text-ink-soft transition-colors hover:text-ink ${
              selected ? "text-ink" : ""
            }`}
          >
            <RecordStrip record={turn.record} />
          </button>
        </div>
      )}
    </li>
  );
}

/** The execution record folded into one line under the answer. */
function RecordStrip({ record }: { record: ExecutionRecord }) {
  const { cache, memory, retrieval, llm, context } = record;

  // Each item names the component's outcome in words; the glyph beside it
  // carries the same status as the inspector.
  const outcome = (name: "memory" | "retrieval", used: string) => {
    const reading = componentStatus(record, name);
    return reading.kind === "off" ? `${COMPONENTS[name].label} ${reading.label.toLowerCase()}` : used;
  };
  const items = [
    {
      component: "cache" as const,
      text: isTurnedOff(record, "cache") ? "Cache off" : cache.hit ? "Cache hit" : "Cache miss",
    },
    {
      component: "memory" as const,
      text: outcome("memory", `${memory.used_count} of ${memory.entries.length} memories`),
    },
    { component: "retrieval" as const, text: outcome("retrieval", `${retrieval.sources.length} sources`) },
    { component: "llm" as const, text: llm.called ? "Model called" : "Model not called" },
  ];

  return (
    <>
      {items.map((item) => (
        <span key={item.component} className="inline-flex items-center gap-1.5">
          <StatusGlyph component={item.component} kind={componentStatus(record, item.component).kind} />
          {item.text}
        </span>
      ))}
      <span className="tabular-nums">{formatCount(context.estimated_tokens)} tokens</span>
      <span className="tabular-nums">{formatMs(record.total_duration_ms)}</span>
    </>
  );
}
