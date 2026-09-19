import type { ExecutionConfig } from "@/types/api";

export type LabComponent = "memory" | "retrieval" | "cache";

export const LAB_COMPONENTS: LabComponent[] = ["memory", "retrieval", "cache"];

export interface LabEntry {
  product: string;
  summary: string;
  why: string;
  stores: string;
  retrieved: string;
  call: string;
  improves: string;
  costs: string;
  caveat: string;
  experiment: { message: string; config: ExecutionConfig; instructions: string };
}

// Explanations are grounded in PLAN.md's tradeoff table and the Iris notes in
// CLAUDE.md; the numbers beside them come from the running backend.
export const LAB: Record<LabComponent, LabEntry> = {
  memory: {
    product: "Agent Memory",
    summary: "Remembers what this customer said before, so “again” means something.",
    why: "Many support questions only make sense with history. “My API is slow again” points at a report from two weeks ago. Without memory the model has to treat it as a brand-new problem.",
    stores:
      "Session events, meaning each turn of a conversation, and long-term memories: durable facts such as past issues, usage patterns, and preferences, each tagged with topics.",
    retrieved:
      "Each request searches the customer's long-term memories and scores them for relevance to the message. Only memories above the relevance threshold reach the model; the rest are listed as left out.",
    call: `await memory.search_long_term_memory_async(
    request={"text": message, "filter": {...}},
)`,
    improves: "Historical awareness, personalization, and continuity across sessions.",
    costs:
      "Latency on every request, and relevance is hard: a stale or wrongly matched memory actively misleads the model.",
    caveat:
      "Session events are promoted to long-term memory asynchronously, minutes later, so the demo seeds long-term memories directly.",
    experiment: {
      message: "My API is slow again.",
      config: { memory_enabled: false, retrieval_enabled: true, cache_enabled: false },
      instructions:
        "Loads the message with memory and cache off. Send it, turn memory back on, and send it again. Compare what reached the model.",
    },
  },
  retrieval: {
    product: "Context Retriever",
    summary: "Fetches live account data the model can't know on its own.",
    why: "The model knows nothing about this customer's plan, usage, tickets, or regional incidents. Retrieval pulls those records at request time, so the answer comes from data rather than a guess.",
    stores:
      "Nothing of its own. It reads records already in Redis under key templates such as customer:{id}, and generates MCP tools from the fields you index.",
    retrieved:
      "Tools are generated per entity: get_<entity>_by_id, filter_<entity>_by_<field>, search_<entity>_by_text, and find_<entity>_by_<field>_range. Each request calls the ones it needs and unwraps the result before it leaves the retrieval layer.",
    call: `await tools.query_tool(
    agent_key=...,
    tool_name="filter_subscription_by_customer_id",
    arguments={"customer_id": "CUST-1001"},
)`,
    improves: "Accuracy, and access to live application data.",
    costs: "Extra round trips, more tokens in the prompt, and a schema to keep in step with your data.",
    caveat:
      "A field belongs to exactly one index type (TAG, TEXT, or NUMERIC), and that type decides which tool is generated.",
    experiment: {
      message: "What plan am I currently on?",
      config: { memory_enabled: true, retrieval_enabled: false, cache_enabled: false },
      instructions:
        "Loads the message with retrieval and cache off. The model has no account data, so it can't name the plan. Turn retrieval on and send it again.",
    },
  },
  cache: {
    product: "LangCache",
    summary: "Answers a repeated question without calling the model.",
    why: "Support questions repeat in different words. A semantic cache matches by meaning, so a close enough question gets the stored answer back in milliseconds, with no model call and no tokens spent.",
    stores: "Prompt and response pairs, indexed by an embedding of the prompt.",
    retrieved:
      "Before anything else runs, the message is compared with cached prompts. At or above the similarity threshold it's a hit: the stored answer is returned and memory, retrieval, and the model are all skipped. After a miss, the new answer is stored.",
    call: `hit = await cache.search_async(prompt=message)   # {} on a miss
await cache.set_async(prompt=message, response=answer)`,
    improves: "Latency and token cost on repeated questions.",
    costs:
      "Threshold tuning. A near miss above the threshold returns a subtly wrong answer, and stored answers go stale until they're invalidated.",
    caveat:
      "The similarity threshold is fixed when the LangCache service is created (0.5 to 1.0, default 0.92). It isn't a per-request setting.",
    experiment: {
      message: "How do I reset my API key?",
      config: { memory_enabled: true, retrieval_enabled: true, cache_enabled: true },
      instructions:
        "Loads the message with every component on. Send it once to fill the cache, then send it again, first as-is and then in other words.",
    },
  },
};
