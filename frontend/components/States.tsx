"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";

export function ReportSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading report">
      <div className="space-y-3">
        <div className="skeleton h-4 w-32" />
        <div className="skeleton h-10 w-72" />
        <div className="skeleton h-4 w-full max-w-xl" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
        <div className="surface flex h-96 items-center justify-center">
          <div className="skeleton h-48 w-48 rounded-full" />
        </div>
        <div className="surface space-y-4 p-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-6 w-full" />
          ))}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="surface h-64 p-4">
            <div className="skeleton h-5 w-24" />
            <div className="skeleton mt-4 h-20 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading results">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="surface p-5">
          <div className="skeleton h-4 w-2/3" />
          <div className="skeleton mt-3 h-3 w-1/3" />
        </div>
      ))}
    </div>
  );
}

/** Shows a friendly message; for rate limits it counts down to the retry time. */
export function ErrorState({
  error,
  onRetry,
  title = "Something went wrong",
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const retryAfter = apiError?.retryAfter ?? 0;
  const rateLimited = apiError?.status === 429;
  const [remaining, setRemaining] = useState(retryAfter);

  useEffect(() => {
    setRemaining(retryAfter);
    if (!retryAfter) return;
    const id = setInterval(() => setRemaining((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [retryAfter]);

  const message = error instanceof Error ? error.message : "An unexpected error occurred.";
  const notFound = apiError?.status === 404;

  return (
    <div role="alert" className="surface mx-auto max-w-xl p-8 text-center">
      <p className="text-lg font-semibold text-zinc-100">{notFound ? "Repository not found" : rateLimited ? "Slow down a little" : title}</p>
      <p className="mt-2 text-sm text-zinc-400">{message}</p>
      {rateLimited && remaining > 0 && (
        <p className="mt-3 text-sm tabular-nums text-caution-400">Try again in {remaining}s</p>
      )}
      {onRetry && !(rateLimited && remaining > 0) && !notFound && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-6 rounded-xl border border-white/15 px-4 py-2 text-sm text-zinc-200 transition hover:border-radar-400/50 hover:text-radar-300"
        >
          Try again
        </button>
      )}
    </div>
  );
}
