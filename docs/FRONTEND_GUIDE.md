# ContextDesk Lab — Frontend Codebase Guide

A guided reading of the frontend: what each file does, why it is shaped that
way, and where to touch it when you want to change something.

`ARCHITECTURE.md` explains the *design* of the whole system, and
`CODEBASE_GUIDE.md` walks the backend code. This file walks the frontend code.

The frontend has one job: render the execution record that comes back with
every response, next to the response, without hiding any component behind the
chat. It owns no business logic. Every number on screen comes from the backend,
and the frontend's work is choosing how to *show* it honestly.

---

## Read it in this order

About 3,300 lines of TypeScript and CSS. A third of it is the inspector, and
most of the rest is pages that reuse the inspector's pieces.

| # | File | Why it comes here |
|---|---|---|
| 1 | `types/api.ts` | The backend's models, mirrored. The execution record's shape already matches the inspector's sections. |
| 2 | `lib/components.ts` | Component identity (name, color) and the status rules, including the Off vs Skipped distinction. Small and load-bearing. |
| 3 | `components/status.tsx` | The status glyph: the one visual device used on every page. |
| 4 | `lib/api.ts`, `hooks/use-backend-resource.ts` | How data gets in: one fetch wrapper, one read hook. |
| 5 | `components/chat/console-provider.tsx` | The only client state that outlives a page: the conversation. |
| 6 | `components/context/` | ★ The inspector. Read `inspector.tsx`, then `signal-path.tsx`, then `context-budget.tsx`. |
| 7 | `components/analytics/`, `compare/`, `lab/` | Pages built from the same pieces. Skim. |
| 8 | `app/globals.css` | The token system, the cascade layers, and the one animation. |

---

## The map

```
frontend/
├── app/                            routes (Next.js App Router)
│   ├── layout.tsx                  fonts, <ConsoleProvider>, <AppHeader>
│   ├── globals.css                 ★ color tokens, dark mode, base layer, motion
│   ├── icon.svg                    favicon: the four channel bars
│   ├── page.tsx                    /            Console
│   ├── compare/page.tsx            /compare     Experiment mode
│   ├── analytics/page.tsx          /analytics   metrics + request history
│   ├── analytics/[requestId]/      /analytics/:id   replay of one request
│   └── lab/                        /lab/[component] — memory, retrieval, cache
│
├── components/
│   ├── app-header.tsx              nav + live component status from /health
│   ├── status.tsx                  ★ StatusGlyph, StatusBadge, ChannelSwatch
│   ├── backend-notice.tsx          a failed backend call, with Retry
│   ├── console-view.tsx            the console's two-pane layout
│   ├── chat/
│   │   ├── console-provider.tsx    ★ conversation state, survives navigation
│   │   ├── chat-panel.tsx          messages, record strip, empty state
│   │   ├── composer.tsx            message box + per-message component toggles
│   │   └── scenarios.ts            the three demo prompts from PLAN.md
│   ├── context/                    the Context Inspector
│   │   ├── inspector.tsx           ★ header + signal path + details
│   │   ├── signal-path.tsx         ★ the six pipeline stations
│   │   ├── context-budget.tsx      ★ what reached the model, what was left out
│   │   ├── component-sections.tsx  cache, memory, retrieval, model sections
│   │   ├── inspector-section.tsx   shared section header + "didn't run" note
│   │   └── score-meter.tsx         0–1 score with its threshold tick
│   ├── analytics/                  metric groups, charts, history, replay
│   ├── compare/compare-view.tsx    four configurations, side by side
│   └── lab/                        per-component explanations + live panel
│
├── lib/
│   ├── api.ts                      fetch wrapper + endpoint functions
│   ├── components.ts               ★ identity, status reading, labels
│   └── format.ts                   ms, tokens, dollars, scores, times
├── hooks/use-backend-resource.ts   the read hook
└── types/api.ts                    mirrors backend/app/models
```

★ = the files worth reading closely.

---

## Routes and what each one calls

| Route | View | Backend calls |
|---|---|---|
| `/` | `ConsoleView`: chat and inspector | `POST /api/chat` per message |
| `/compare` | `CompareView` | `POST /api/chat/compare` |
| `/analytics` | `AnalyticsView` | `GET /api/analytics/summary`, `GET /api/analytics/history?limit=200` |
| `/analytics/[requestId]` | `ReplayView` | `GET /api/analytics/history/{id}` |
| `/lab` | redirects to `/lab/memory` | none |
| `/lab/[component]` | static explanation + `LabLive` | `/health`, summary, history, then one record |
| every page | `AppHeader` | `GET /health` |

Page files are server components that export `metadata` and render one client
view. Everything that talks to the backend is a client component, because the
backend's telemetry is in-process and live. Nothing is worth prerendering or
caching.

`/lab/[component]` is the one statically generated route: `generateStaticParams`
returns the three components and `dynamicParams = false` makes anything else a
404.

---

## Data in: one wrapper, one hook

`lib/api.ts` is the only file that knows the backend's address and paths.

```ts
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

It turns the two ways a call fails into sentences a person can act on. A network
failure becomes "Can't reach the backend at … Start it with: cd backend && uv run
fastapi dev app/main.py", because a stopped backend is the most common state of a
local tool. An HTTP error carries the backend's own `detail`.

Every read goes through `useBackendResource(key, load)`:

```ts
const analytics = useBackendResource("analytics", loadAnalytics);
const replay    = useBackendResource(`record:${id}`, () => api.record(id));
```

Three behaviors to know:

1. **It refetches when `key` changes or `reload()` is called**, and at no other
   time. The loader is wrapped in `useEffectEvent`, so it is deliberately *not* an
   effect dependency. An inline arrow that is new on every render can't cause a
   refetch loop.
2. **Previous data survives a refetch and a failure.** A refresh never flashes
   the page back to empty, and an error after a success shows the error above
   the last good data.
3. **The status is `loading` | `ready` | `error`**, a discriminated union, so
   `data` is only non-optional once the status says it exists.

Writes (sending a message, running a comparison) are plain `async` calls in event
handlers. They don't go through the hook.

---

## State: the conversation

`ConsoleProvider` lives in the root layout, so the conversation survives moving
from the console to analytics and back. It holds:

| State | Notes |
|---|---|
| `turns` | One `ChatTurn` per message: the message, the config it ran with, `pending` / `done` / `error`, and the response plus record |
| `config` | The toggles for the *next* message |
| `selectedTurn` | Which turn the inspector shows. It defaults to the latest |
| `draft` | The composer text. The Lab's "Try it" writes here through `prepare()` |
| `sessionId` | A new one per conversation, so short-term memory doesn't bleed across |

**The config is captured per turn.** Flipping a toggle after sending must not
rewrite what an earlier message ran with, and the chat shows "Sent without
memory" under any turn that ran with a component off.

The conversation is in-memory and a reload clears it. The records themselves
are still in the backend, so every past request stays reachable from Analytics
until the backend restarts.

---

## The visual system

The rules are few, and every page depends on them.

### One color per component

Defined once in `globals.css` and mapped to Tailwind colors in `@theme inline`,
so `bg-memory`, `border-cache`, and so on all work:

| Component | Light | Dark |
|---|---|---|
| Memory | `#e87ba4` | `#d55181` |
| Retrieval | `#008300` | `#008300` |
| Cache | `#eda100` | `#c98500` |
| Model | `#2a78d6` | `#3987e5` |

That color follows the component everywhere: the composer toggle, the inspector
section, the budget bar segment, the chart series, the Lab tab. The four were
chosen *as a set* and checked for colorblind separation across all pairs in both
themes. Swapping one without re-checking the set can quietly make two
components indistinguishable.

Everything else is neutral: grey ink on cool paper. If something on screen is
saturated, it names a component. The one exception is `--critical`, which is
reserved for failure.

**Text never wears a component color.** Labels stay in ink, and identity comes
from a swatch or glyph beside them, because the lighter hues (amber, pink) are
unreadable as text.

### Status is the fill, never the hue

`StatusGlyph` in `components/status.tsx`:

| Fill | Status | Label |
|---|---|---|
| solid | `ok`: the real service ran | OK |
| half-filled | `stub`: an in-process fake stood in | Stub |
| hollow ring | `disabled`: it didn't run | Off, Skipped, or Not run |
| red with a cross | `unavailable`: it was asked and failed | Unavailable |

The hue still says *which* component, and the fill says *what state*. A word
label always accompanies the glyph, visibly or as screen-reader text with a
`title`, so state is never carried by shape alone.

### Off vs Skipped

The backend marks both "the user turned it off" and "a cache hit made it
unnecessary" as `disabled`, and sets `skipped_reason` in **both** cases
(`"memory_enabled=false for this request"` vs `"response served from the
semantic cache"`). So the presence of a reason can't tell them apart. The
config can:

```ts
export function isTurnedOff(record: ExecutionRecord, name: ComponentName) {
  const toggle = TOGGLEABLE.find((candidate) => candidate.name === name);
  return toggle !== undefined && !record.execution_config[toggle.key];
}
```

`componentStatus(record, name)` combines the two, and every surface that reads a
record uses it. History rows don't carry `execution_config`, so
`history-table.tsx` reads the same fact from `config_label`, which lists exactly
the enabled components.

### Type and motion

Atkinson Hyperlegible Next for everything, and its Mono cut only for literal code
such as tool names, request ids, and raw context. The zeros are slashed; that's the
typeface, which distinguishes `0` from `O` in ids like `CUST-1001`.

There is one orchestrated animation: when a record arrives, the signal path's
stations light up in pipeline order (`.station-light`, 70 ms apart, keyed by
request id so it replays per record). The only other motion is the three
"working" dots while a request is in flight. Both are off under
`prefers-reduced-motion`.

---

## Walking the inspector

`Inspector` is a header, a `SignalPath`, and `InspectorDetails`. The replay page
reuses `InspectorDetails` directly and replaces the signal path with its
waterfall.

```
Inspector
├── header          the message, request id, time, config, total duration, "Open replay"
├── SignalPath      six fixed stations
└── InspectorDetails
    ├── (cache-hit note, record.error)
    ├── ContextBudget   what reached the model, and what was left out
    ├── CacheSection    hit/miss, similarity vs threshold, matched prompt, estimated saving
    ├── MemorySection   each memory, its relevance, used or left out
    ├── RetrievalSection each tool call, its arguments, the rows it returned
    └── ModelSection    model, tokens in/out, estimated cost
```

The sections follow pipeline order. "What reached the model" comes first because
it answers the project's central question before the detail does.

### `signal-path.tsx`

Six stations, **fixed**, in the order the chat service runs them:

```ts
"cache lookup" → "memory" → "structured retrieval" → "context assembly" → "llm" → "cache store"
```

Each station finds its step in `record.steps` **by name**. The list is fixed
rather than built from `record.steps`, so a request that ended early still shows
every station, and what it skipped is visible as hollow. A station with no step
reads "Not run", or "Off" if the config turned its component off.

Each station also gets a duration bar scaled to the slowest step, so the
expensive step is obvious at a glance. With a real model that's nearly always
the model. The grid is container-query driven (`@container`, 2 → 3 → 6
columns), so it adapts to the inspector's width, not the viewport's.

### `context-budget.tsx`

The bar's track is the token budget. Included sections are solid segments in
their origin's color, and excluded sections that carry a token estimate are
drawn after them as dashed ghosts. The scale is:

```ts
const scale = Math.max(budget, used + ghostTokens, 1);
```

so a left-out section that would have overflowed the budget still gets its true
proportion instead of being clipped. Below the bar, each included section
expands to the exact text the model saw, and each left-out item shows its reason
(`EXCLUSION_REASONS` in `lib/components.ts`) and the backend's detail, for
example "Below relevance threshold, relevance 0.5 < 0.6".

### `component-sections.tsx`

Each section is `InspectorSection` (swatch, title, status badge, duration) around
a body. When the component didn't produce anything, the body is `NotRunNote`,
which says whether it was turned off, skipped (and why), or failed (with the
error). A missing panel is never left unexplained.

Two things worth noticing:

- **Memory's "used" is read from the context, not guessed.** An entry is used if
  `context.included` has a section named `memory: <id>`.
- **The cache's saving is the backend's estimate, not the frontend's.**
  `CacheSavings` fetches the summary and shows `average_llm_ms` and
  `estimated_saved_usd / llm_calls_avoided`. The frontend never re-derives cost,
  so the inspector and analytics can't disagree.

---

## Where the numbers come from

Every figure is a field the backend sent. The frontend formats (`lib/format.ts`)
but never computes a metric.

| On screen | Field |
|---|---|
| Total duration (inspector, replay) | `record.total_duration_ms` |
| Station and waterfall durations | `record.steps[].duration_ms` |
| "272 of 1,200 token budget" | `context.estimated_tokens`, `context.budget_tokens` |
| Budget bar segments | `context.included[].estimated_tokens`, `context.excluded[].estimated_tokens` |
| Similarity meter and threshold tick | `cache.similarity`, `cache.threshold` |
| Memory relevance | `memory.entries[].relevance` |
| Model tokens and cost | `llm.input_tokens`, `llm.output_tokens`, `llm.estimated_cost_usd` |
| Cache saving | `summary.latency.average_llm_ms`, `summary.llm.estimated_saved_usd / summary.cache.llm_calls_avoided` |
| Analytics groups | `/api/analytics/summary`, one row per field |
| Latency chart | `history.items[].total_duration_ms`, colored by `cache_hit` / `llm_called` |
| Header status | `/health` |

`formatMs` switches precision with magnitude (`0.06 ms`, `18.4 ms`, `812 ms`,
`1.24 s`). Stub steps finish in hundredths of a millisecond while a real model
takes seconds, and one fixed precision would round one end or the other into
nonsense. Costs are always shown with `~` and "estimate".

---

## Recipes

### Show a new field from the execution record

Add it to the matching interface in `types/api.ts`, then render it in the section
that owns that component in `component-sections.tsx`. If it's a number, add a
formatter to `lib/format.ts` rather than formatting inline.

### Add a pipeline step

The backend's `add_step("<name>", …)` name is a contract. Add a station to
`STATIONS` in `signal-path.tsx` (with its `purpose` line and `result` summary)
and a label to `STEPS` in `analytics/step-waterfall.tsx`. A step the frontend
doesn't know still appears in the waterfall under its raw name, but it won't
appear in the signal path.

### Add an exclusion reason

Add the value to the `ExclusionReason` union in `types/api.ts`. The
`EXCLUSION_REASONS` record in `lib/components.ts` is typed over that union, so
the build fails until you give it a label. That's intentional.

### Add a page

Create `app/<route>/page.tsx` as a server component that exports `metadata` and
renders a client view from `components/<area>/`. Add it to `NAV` in
`app-header.tsx`. Keep that array `as const` so each `href` stays a literal that
typed routes can check (see Gotchas).

### Change a component's color

Change it in both the light `:root` block and the dark block of `globals.css`,
and update `app/icon.svg`, which can't read CSS variables. Then re-check the
whole set of four for colorblind separation in both themes, not just the color
you changed.

### Add a component to the Lab

Add it to `LAB_COMPONENTS` and `LAB` in `components/lab/lab-content.ts`, and
teach `LabLive`'s `latestContribution`, `UsageFigures`, and
`describeContribution` what "used" means for it. `generateStaticParams` picks up
the new route.

---

## Running and checking it

```bash
cd frontend
npm install
npm run dev              # :3000 — needs the backend on :8000
npm run lint
npx tsc --noEmit
npm run build            # fetches Google Fonts, so it needs network access
```

The backend's CORS policy admits only `http://localhost:3000`. Point the
frontend at a different backend with `NEXT_PUBLIC_API_URL` in
`frontend/.env.local`. Next reads env files from its own directory, not the repo
root's `.env`.

---

## Gotchas

**This is Next.js 16, not the version in your memory.** The authoritative docs
ship inside the package at `node_modules/next/dist/docs/`. `params` is a
`Promise`, route type helpers like `PageProps<"/analytics/[requestId]">` and
`LayoutProps<"/">` are generated globals, and `typedRoutes` is on.

**Typed routes reject a bare `Route` for dynamic segments.** An array typed
`{ href: Route }[]` won't accept `"/lab/memory"`. Declare the array `as const`
and let each literal reach `<Link>`, where it's validated directly. Template
literals like ``href={`/analytics/${id}`}`` are fine.

**The React Compiler is on.** Don't hand-add `useMemo` or `useCallback`. Also
don't mutate a local variable inside a render-time callback (a running total
inside `.map()`); precompute it instead, as `step-waterfall.tsx` does with
`starts`.

**Unlayered CSS beats Tailwind utilities.** Tailwind v4 puts utilities in
`@layer utilities`, and any unlayered rule wins over every layer regardless of
specificity. Global element styles go in `@layer base` in `globals.css`.
Otherwise a utility like `focus-visible:outline-none` silently loses to a
global `:focus-visible` rule.

**The console's panes only scroll independently because of two classes.** The
console `<main>` is `lg:flex-none` (otherwise `flex-1` in the body's flex column
overrides its height) and `lg:grid-rows-[minmax(0,1fr)]` (otherwise the grid row
grows to fit the inspector). Without either, the whole page scrolls and the
header covers the top of the inspector.

**Hidden overlays must be `display: none`, not `visibility: hidden`.** An
invisible tooltip still counts toward the page's scroll width and adds a
horizontal scrollbar at phone widths. Likewise, a grid column containing a
`<pre>` needs `min-w-0`, or the code block widens the column past the viewport.

**Step names are a contract with the backend.** Renaming `"structured
retrieval"` in `chat_service.py` without updating `signal-path.tsx` leaves that
station permanently reading "Not run".

**Repeating a message hits the cache,** and so does a paraphrase: in stub mode, a
word overlap of 0.6 is enough. That's the cache working, but it's easy to
mistake for a bug when you meant to test something else. Turn the Cache toggle
off to isolate another component.

**Stub timings are hundredths of a millisecond.** The duration bars are still
proportional, but the absolute numbers only become meaningful against real
services and a real model.

**`next dev` rewrites `frontend/AGENTS.md` and `frontend/CLAUDE.md`.** Commit
them rather than fighting them.

**The font warnings are harmless.** "Failed to find font override values for
Atkinson Hyperlegible" means Next can't size-match a fallback font for these
faces. The fonts still load.

---

## What is not here yet

- **No frontend tests.** Lint, the type checker, and a production build are the
  checks today. The behavior most worth pinning is `lib/components.ts`'s status
  reading (Off vs Skipped) and `ContextBudget`'s scale.
- **Model answers render as plain text** with line breaks preserved. A real
  model's Markdown shows as raw text.
- **One customer.** The console always sends as `CUST-1001`, the backend's
  default and the customer the demo scenarios are written against.
- **The conversation isn't persisted.** A reload clears the chat, though the
  records stay in Analytics until the backend restarts.
- **No theme toggle.** The UI follows the operating system's light or dark
  setting.
