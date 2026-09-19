"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { describeError } from "@/lib/api";

export type Resource<T> =
  | { status: "loading"; data?: undefined; error?: undefined }
  | { status: "ready"; data: T; error?: undefined }
  | { status: "error"; data?: T; error: string };

/**
 * Loads one backend resource and refetches whenever `key` changes or
 * `reload()` is called. The previous data stays in place during a refetch, so
 * a refresh never flashes the page back to an empty state.
 */
export function useBackendResource<T>(key: string, load: () => Promise<T>) {
  const [resource, setResource] = useState<Resource<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const runLoad = useEffectEvent(load);

  useEffect(() => {
    let cancelled = false;
    runLoad().then(
      (data) => {
        if (!cancelled) setResource({ status: "ready", data });
      },
      (error: unknown) => {
        if (!cancelled)
          setResource((previous) => ({
            status: "error",
            data: previous.data,
            error: describeError(error),
          }));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [key, attempt]);

  return { ...resource, reload: () => setAttempt((n) => n + 1) };
}
