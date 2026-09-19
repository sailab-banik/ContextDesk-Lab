import { LabTabs } from "@/components/lab/lab-tabs";

export default function LabLayout({ children }: LayoutProps<"/lab">) {
  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 sm:py-10">
      <h1 className="text-3xl font-bold tracking-[-0.02em]">Technology lab</h1>
      <p className="mt-1.5 max-w-prose text-[15px] text-ink-soft">
        Why each Redis Iris component exists, what it stores, how it&apos;s queried, and what it
        changed in the requests you&apos;ve sent.
      </p>
      <div className="mt-6">
        <LabTabs />
      </div>
      {children}
    </main>
  );
}
