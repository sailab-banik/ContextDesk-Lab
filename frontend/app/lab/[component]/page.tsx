import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { LAB, LAB_COMPONENTS, type LabComponent } from "@/components/lab/lab-content";
import { LabLive } from "@/components/lab/lab-live";

export const dynamicParams = false;

export function generateStaticParams() {
  return LAB_COMPONENTS.map((component) => ({ component }));
}

function isLabComponent(value: string): value is LabComponent {
  return (LAB_COMPONENTS as string[]).includes(value);
}

export async function generateMetadata({ params }: PageProps<"/lab/[component]">): Promise<Metadata> {
  const { component } = await params;
  return { title: isLabComponent(component) ? LAB[component].product : "Lab" };
}

export default async function LabComponentPage({ params }: PageProps<"/lab/[component]">) {
  const { component } = await params;
  if (!isLabComponent(component)) notFound();
  const entry = LAB[component];

  return (
    <div className="mt-8 grid gap-10 lg:grid-cols-[3fr_2fr]">
      <article className="min-w-0">
        <h2 className="max-w-[24ch] text-[28px] leading-[1.15] font-bold tracking-[-0.02em] text-balance">
          {entry.summary}
        </h2>

        <dl className="mt-8 flex max-w-prose flex-col gap-6 text-[15px] leading-6">
          <div>
            <dt className="font-bold">Why it exists</dt>
            <dd className="mt-1 text-ink-soft">{entry.why}</dd>
          </div>
          <div>
            <dt className="font-bold">What it stores</dt>
            <dd className="mt-1 text-ink-soft">{entry.stores}</dd>
          </div>
          <div>
            <dt className="font-bold">How it&apos;s queried</dt>
            <dd className="mt-1 text-ink-soft">{entry.retrieved}</dd>
            <dd>
              <pre className="mt-3 overflow-x-auto rounded-lg border border-rule bg-surface px-4 py-3 font-mono text-[13px] leading-5">
                {entry.call}
              </pre>
            </dd>
          </div>
        </dl>

        <div className="mt-8 grid max-w-prose gap-6 border-t border-rule pt-6 sm:grid-cols-2">
          <div>
            <h3 className="text-sm font-bold">What it improves</h3>
            <p className="mt-1 text-sm leading-6 text-ink-soft">{entry.improves}</p>
          </div>
          <div>
            <h3 className="text-sm font-bold">What it costs</h3>
            <p className="mt-1 text-sm leading-6 text-ink-soft">{entry.costs}</p>
          </div>
        </div>

        <p className="mt-6 max-w-prose rounded-lg bg-surface-sunk px-4 py-3 text-sm leading-6 text-ink-soft">
          {entry.caveat}
        </p>
      </article>

      <div className="lg:sticky lg:top-20 lg:self-start">
        <LabLive component={component} />
      </div>
    </div>
  );
}
