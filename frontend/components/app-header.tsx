"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusGlyph } from "@/components/status";
import { useBackendResource } from "@/hooks/use-backend-resource";
import { api } from "@/lib/api";
import { COMPONENTS, readStatus } from "@/lib/components";

const NAV = [
  { href: "/", label: "Console", matches: (path: string) => path === "/" },
  { href: "/compare", label: "Compare", matches: (path: string) => path.startsWith("/compare") },
  { href: "/analytics", label: "Analytics", matches: (path: string) => path.startsWith("/analytics") },
  { href: "/lab/memory", label: "Lab", matches: (path: string) => path.startsWith("/lab") },
] as const;

export function LogoMark({ className = "size-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden className={className}>
      <rect x="1" y="7" width="3.5" height="12" rx="1.2" fill="var(--memory)" />
      <rect x="5.83" y="3" width="3.5" height="16" rx="1.2" fill="var(--retrieval)" />
      <rect x="10.66" y="10" width="3.5" height="9" rx="1.2" fill="var(--cache)" />
      <rect x="15.5" y="1" width="3.5" height="18" rx="1.2" fill="var(--llm)" />
    </svg>
  );
}

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-rule bg-surface/90 backdrop-blur-md">
      <div className="flex flex-wrap items-center gap-x-4 px-4 sm:gap-x-8 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5 rounded-md">
          <LogoMark />
          <span className="text-[15px] font-bold tracking-[-0.01em] max-sm:sr-only">
            ContextDesk Lab
          </span>
        </Link>

        <nav aria-label="Main" className="flex h-14 min-w-0 items-stretch gap-1 overflow-x-auto">
          {NAV.map((item) => {
            const active = item.matches(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`relative flex items-center rounded-md px-2.5 text-sm font-medium transition-colors ${
                  active ? "text-ink" : "text-ink-soft hover:text-ink"
                }`}
              >
                {item.label}
                {active && (
                  <span aria-hidden className="absolute inset-x-2.5 -bottom-px h-0.5 rounded-full bg-ink" />
                )}
              </Link>
            );
          })}
        </nav>

        <ComponentHealth />
      </div>
    </header>
  );
}

function ComponentHealth() {
  const health = useBackendResource("health", api.health);

  if (health.status === "error" && !health.data) {
    return (
      <p
        role="status"
        title={health.error}
        className="flex shrink-0 items-center gap-1.5 pb-3 text-sm text-critical-ink sm:ml-auto sm:pb-0"
      >
        <StatusGlyph kind="unavailable" />
        Backend offline
        <button
          type="button"
          onClick={health.reload}
          className="ml-1 rounded-md px-1.5 py-0.5 text-ink-soft underline decoration-rule-strong underline-offset-2 hover:text-ink"
        >
          Retry
        </button>
      </p>
    );
  }

  return (
    <ul
      aria-label="Component status"
      className="flex shrink-0 items-center gap-4 pb-3 max-sm:w-full sm:ml-auto sm:pb-0 lg:gap-5"
    >
      {(health.data?.components ?? []).map((component) => {
        const reading = readStatus(component.status);
        const { label } = COMPONENTS[component.name];
        return (
          <li
            key={component.name}
            title={`${label}: ${reading.label}. ${component.detail}`}
            className="flex items-center gap-1.5 text-sm"
          >
            <StatusGlyph component={component.name} kind={reading.kind} />
            <span>{label}</span>
            <span className="text-ink-faint max-lg:sr-only">{reading.label}</span>
          </li>
        );
      })}
    </ul>
  );
}
