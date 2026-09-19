"use client";

import { ChatPanel } from "@/components/chat/chat-panel";
import { useConsole } from "@/components/chat/console-provider";
import { Inspector } from "@/components/context/inspector";

export function ConsoleView() {
  const { turns, selectedTurn } = useConsole();

  // While a message runs, keep showing the last finished record (dimmed)
  // rather than blanking the inspector.
  const shownTurn =
    selectedTurn?.record ? selectedTurn : turns.findLast((turn) => turn.record !== undefined);

  return (
    <main className="grid flex-1 lg:h-[calc(100dvh-3.5rem)] lg:flex-none lg:grid-cols-[minmax(22rem,5fr)_7fr] lg:grid-rows-[minmax(0,1fr)]">
      {/* On narrow screens the chat is a fixed-height pane, so the composer stays in reach above the inspector. */}
      <div className="flex h-[85dvh] flex-col border-rule lg:h-auto lg:min-h-0 lg:border-r">
        <ChatPanel />
      </div>
      <aside
        aria-label="Context inspector"
        className="border-t border-rule bg-surface px-4 py-6 sm:px-8 lg:overflow-y-auto lg:border-t-0"
      >
        <Inspector record={shownTurn?.record} pending={selectedTurn?.status === "pending"} />
      </aside>
    </main>
  );
}
