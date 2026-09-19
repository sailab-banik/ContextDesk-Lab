"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

import { api, describeError } from "@/lib/api";
import type { ExecutionConfig, ExecutionRecord } from "@/types/api";

/** One message and everything that came back for it. */
export interface ChatTurn {
  id: string;
  message: string;
  config: ExecutionConfig;
  status: "pending" | "done" | "error";
  response?: string;
  record?: ExecutionRecord;
  error?: string;
}

const FULL_SYSTEM: ExecutionConfig = {
  memory_enabled: true,
  retrieval_enabled: true,
  cache_enabled: true,
};

interface ConsoleState {
  turns: ChatTurn[];
  selectedTurn: ChatTurn | undefined;
  selectTurn: (id: string) => void;
  config: ExecutionConfig;
  toggleComponent: (key: keyof ExecutionConfig) => void;
  draft: string;
  setDraft: (text: string) => void;
  pending: boolean;
  send: (message: string) => void;
  retry: (id: string) => void;
  newConversation: () => void;
  /** Load a message and configuration into the composer without sending it. */
  prepare: (message: string, config: ExecutionConfig) => void;
}

const ConsoleContext = createContext<ConsoleState | null>(null);

function newSessionId() {
  return `session-${Date.now().toString(36)}`;
}

function newTurnId() {
  return `turn-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

// Lives in the root layout so the conversation survives moving between the
// console, analytics, and the lab.
export function ConsoleProvider({ children }: { children: ReactNode }) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [config, setConfig] = useState<ExecutionConfig>(FULL_SYSTEM);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState(newSessionId);

  const pending = turns.some((turn) => turn.status === "pending");
  const selectedTurn = turns.find((turn) => turn.id === selectedId) ?? turns.at(-1);

  function updateTurn(id: string, changes: Partial<ChatTurn>) {
    setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, ...changes } : turn)));
  }

  async function run(turn: ChatTurn) {
    try {
      const result = await api.sendMessage({
        message: turn.message,
        session_id: sessionId,
        // The configuration is captured per turn: flipping a toggle afterwards
        // must not rewrite what an earlier message was run with.
        config: turn.config,
      });
      updateTurn(turn.id, { status: "done", response: result.response, record: result.execution });
    } catch (error) {
      updateTurn(turn.id, { status: "error", error: describeError(error) });
    }
  }

  function send(message: string) {
    const text = message.trim();
    if (!text || pending) return;
    const turn: ChatTurn = { id: newTurnId(), message: text, config, status: "pending" };
    setTurns((current) => [...current, turn]);
    setSelectedId(turn.id);
    setDraft("");
    void run(turn);
  }

  function retry(id: string) {
    const turn = turns.find((candidate) => candidate.id === id);
    if (!turn || pending) return;
    updateTurn(id, { status: "pending", error: undefined });
    setSelectedId(id);
    void run(turn);
  }

  function newConversation() {
    setTurns([]);
    setSelectedId(null);
    // A fresh session id keeps the new conversation's short-term memory
    // separate from the old one; long-term memory is per customer and stays.
    setSessionId(newSessionId());
  }

  const value: ConsoleState = {
    turns,
    selectedTurn,
    selectTurn: setSelectedId,
    config,
    toggleComponent: (key) => setConfig((current) => ({ ...current, [key]: !current[key] })),
    draft,
    setDraft,
    pending,
    send,
    retry,
    newConversation,
    prepare: (message, nextConfig) => {
      setDraft(message);
      setConfig(nextConfig);
    },
  };

  return <ConsoleContext value={value}>{children}</ConsoleContext>;
}

export function useConsole(): ConsoleState {
  const state = useContext(ConsoleContext);
  if (!state) throw new Error("useConsole must be used inside <ConsoleProvider>");
  return state;
}
