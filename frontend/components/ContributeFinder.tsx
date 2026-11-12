"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatCount, timeAgo } from "@/lib/format";
import type { ContributionsResponse } from "@/lib/types";
import { ErrorState, ListSkeleton } from "./States";

const LABELS = ["good first issue", "help wanted", "beginner", "first-timers-only", "easy"];

export function ContributeFinder() {
  const [label, setLabel] = useState(LABELS[0]);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ContributionsResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .contributions(label, submitted, page)
      .then((res) => !cancelled && setData(res))
      .catch((err) => !cancelled && (setData(null), setError(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [label, submitted, page, attempt]);

  function search(e: FormEvent) {
    e.preventDefault();
    setPage(1);
    setSubmitted(query);
  }

  return (
    <div className="space-y-6">
      <form onSubmit={search} className="surface flex flex-col gap-3 p-4 md:flex-row md:items-end">
        <label className="flex flex-col gap-1 text-xs text-zinc-400 md:w-56">
          Label
          <select
            value={label}
            onChange={(e) => {
              setPage(1);
              setLabel(e.target.value);
            }}
            className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-radar-500/40"
          >
            {LABELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1 text-xs text-zinc-400">
          Keyword (optional)
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. documentation, tests, typo"
            maxLength={120}
            className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-radar-500/40"
          />
        </label>
        <button type="submit" className="rounded-lg bg-gradient-to-r from-radar-500 to-signal-500 px-5 py-2 text-sm font-semibold text-zinc-950 hover:brightness-110">
          Search
        </button>
      </form>

      {loading && <ListSkeleton />}
      {!loading && error != null && <ErrorState error={error} onRetry={() => setAttempt((n) => n + 1)} title="Could not load issues" />}
      {!loading && !error && data && (
        <>
          <p className="text-sm text-zinc-500" aria-live="polite">
            {formatCount(data.total_count)} open issues match. Showing page {data.page}.
          </p>
          {data.items.length === 0 && <p className="surface p-6 text-sm text-zinc-400">No issues match these filters. Try another label or keyword.</p>}
          <ul className="space-y-3">
            {data.items.map((item) => (
              <li key={item.url} className="surface p-5 transition hover:border-white/20">
                <a href={item.url} target="_blank" rel="noreferrer" className="text-base font-medium text-zinc-100 hover:text-radar-300">
                  {item.title}
                </a>
                <p className="mt-1 text-xs text-zinc-500">
                  <span className="text-zinc-300">{item.repo}</span> · #{item.number} · opened {timeAgo(item.created_at)} · {item.comments} comments
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.labels.map((l) => (
                    <span key={l} className="rounded-full border border-white/10 px-2.5 py-0.5 text-[11px] text-zinc-400">
                      {l}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
          <nav aria-label="Pagination" className="flex items-center justify-between pt-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-300 enabled:hover:border-radar-400/50 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-zinc-500">Page {page}</span>
            <button
              type="button"
              disabled={data.items.length < 20 || page >= 10}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-zinc-300 enabled:hover:border-radar-400/50 disabled:opacity-40"
            >
              Next
            </button>
          </nav>
        </>
      )}
    </div>
  );
}
