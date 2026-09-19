"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { LAB, LAB_COMPONENTS } from "@/components/lab/lab-content";
import { ChannelSwatch } from "@/components/status";

export function LabTabs() {
  const pathname = usePathname();

  return (
    <nav aria-label="Components" className="flex gap-1 overflow-x-auto border-b border-rule">
      {LAB_COMPONENTS.map((component) => {
        const href = `/lab/${component}` as const;
        const active = pathname === href;
        return (
          <Link
            key={component}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`relative flex items-center gap-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap ${
              active ? "text-ink" : "text-ink-soft hover:text-ink"
            }`}
          >
            <ChannelSwatch component={component} />
            {LAB[component].product}
            {active && <span aria-hidden className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-ink" />}
          </Link>
        );
      })}
    </nav>
  );
}
