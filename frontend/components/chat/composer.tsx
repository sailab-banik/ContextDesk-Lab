"use client";

import { useConsole } from "@/components/chat/console-provider";
import { COMPONENTS, TOGGLEABLE } from "@/lib/components";

export function Composer() {
  const { draft, setDraft, send, pending, config, toggleComponent } = useConsole();

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        send(draft);
      }}
      className="rounded-xl border border-rule-strong bg-surface transition-shadow has-[textarea:focus-visible]:border-ink-soft has-[textarea:focus-visible]:shadow-[0_0_0_3px_color-mix(in_srgb,var(--llm)_18%,transparent)]"
    >
      <label htmlFor="message" className="sr-only">
        Message
      </label>
      <textarea
        id="message"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            send(draft);
          }
        }}
        rows={2}
        placeholder="Ask about your account, usage, or API…"
        className="block max-h-40 min-h-16 w-full resize-none bg-transparent px-4 pt-3 text-[15px] leading-6 outline-none focus-visible:outline-none field-sizing-content placeholder:text-ink-faint"
      />

      <div className="flex flex-wrap items-center gap-2 px-2.5 pt-1 pb-2.5">
        <fieldset className="flex flex-wrap items-center gap-1.5">
          <legend className="sr-only">Components used for the next message</legend>
          {TOGGLEABLE.map(({ name, key }) => {
            const on = config[key];
            const { label, color } = COMPONENTS[name];
            return (
              <button
                key={key}
                type="button"
                aria-pressed={on}
                onClick={() => toggleComponent(key)}
                title={`${label} is ${on ? "on" : "off"} for the next message`}
                className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-sm transition-colors ${
                  on
                    ? "border-rule-strong bg-surface-sunk text-ink"
                    : "border-dashed border-rule-strong text-ink-faint"
                }`}
              >
                <span
                  aria-hidden
                  className="size-2.5 rounded-full border-[1.5px]"
                  style={{ borderColor: on ? color : "var(--rule-strong)", background: on ? color : "transparent" }}
                />
                {label}
              </button>
            );
          })}
        </fieldset>

        <button
          type="submit"
          disabled={pending || !draft.trim()}
          className="ml-auto inline-flex h-8 items-center rounded-full bg-ink px-4 text-sm font-semibold text-surface transition-opacity disabled:opacity-35"
        >
          {pending ? "Sending…" : "Send"}
        </button>
      </div>
    </form>
  );
}
