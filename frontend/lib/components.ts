import type {
  ComponentName,
  ComponentStatus,
  ExclusionReason,
  ExecutionConfig,
  ExecutionRecord,
} from "@/types/api";

// Each component owns one color, and that color follows it everywhere: the
// toggle, the inspector section, the context budget, the charts. The four
// hues were validated as a set for colorblind separation in both themes.
export const COMPONENTS: Record<ComponentName, { label: string; product: string; color: string }> =
  {
    memory: { label: "Memory", product: "Agent Memory", color: "var(--memory)" },
    retrieval: { label: "Retrieval", product: "Context Retriever", color: "var(--retrieval)" },
    cache: { label: "Cache", product: "LangCache", color: "var(--cache)" },
    llm: { label: "Model", product: "LLM", color: "var(--llm)" },
  };

export const TOGGLEABLE: { name: ComponentName; key: keyof ExecutionConfig }[] = [
  { name: "memory", key: "memory_enabled" },
  { name: "retrieval", key: "retrieval_enabled" },
  { name: "cache", key: "cache_enabled" },
];

export type StatusKind = "ok" | "stub" | "unavailable" | "off";

export interface StatusReading {
  kind: StatusKind;
  label: string;
}

// "Disabled" covers two different situations in the record: the user turned
// the component off, or an earlier step made it unnecessary. The UI keeps
// them apart, because "I turned this off" and "this didn't need to run" teach
// different things.
export function readStatus(status: ComponentStatus, turnedOff = true): StatusReading {
  switch (status) {
    case "ok":
      return { kind: "ok", label: "OK" };
    case "stub":
      return { kind: "stub", label: "Stub" };
    case "unavailable":
      return { kind: "unavailable", label: "Unavailable" };
    case "disabled":
      return { kind: "off", label: turnedOff ? "Off" : "Skipped" };
  }
}

/** Whether the request's own configuration switched this component off. */
export function isTurnedOff(record: ExecutionRecord, name: ComponentName): boolean {
  const toggle = TOGGLEABLE.find((candidate) => candidate.name === name);
  return toggle !== undefined && !record.execution_config[toggle.key];
}

export function componentStatus(record: ExecutionRecord, name: ComponentName): StatusReading {
  return readStatus(record[name].status, isTurnedOff(record, name));
}

export const EXCLUSION_REASONS: Record<ExclusionReason, string> = {
  no_data: "Nothing returned",
  not_relevant: "Not relevant",
  below_relevance_threshold: "Below relevance threshold",
  context_budget_exceeded: "Over the token budget",
  component_disabled: "Component didn't run",
  component_unavailable: "Component unavailable",
};

// Context sections name their origin; memory and retrieval are the only two
// components that contribute context blocks.
export function originComponent(origin: string): ComponentName {
  return origin === "memory" ? "memory" : "retrieval";
}

export function configLabel(config: ExecutionConfig): string {
  const on = TOGGLEABLE.filter(({ key }) => config[key]).map(({ name }) => COMPONENTS[name].label);
  if (on.length === 0) return "Model only";
  if (on.length === TOGGLEABLE.length) return "Full system";
  return `Model + ${on.join(" + ").toLowerCase()}`;
}
