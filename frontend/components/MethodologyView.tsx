"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorState, ListSkeleton } from "./States";

type Methodology = {
  methodology_version: string;
  categories: { id: string; title: string; weight: number }[];
  checks: { id: string; category: string; title: string; max_points: number; critical_if_missing: boolean; recommendation: string }[];
  grades: Record<string, string>;
  partial_credit: string;
};

export function MethodologyView() {
  const [data, setData] = useState<Methodology | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .methodology()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ListSkeleton rows={5} />;
  if (error || !data) return <ErrorState error={error} title="Could not load the methodology" />;

  return (
    <article className="max-w-4xl space-y-10">
      <header>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-radar-300">Methodology v{data.methodology_version}</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">How the health score works</h1>
        <p className="mt-4 text-zinc-400">
          The score is the sum of points from {data.checks.length} checks across {data.categories.length} categories. Weights add
          up to 100. Each check is pass (full points), partial (half points, rounded down) or fail (zero). Every result in a
          report shows the evidence that produced it, so you can verify it yourself.
        </p>
        <p className="mt-2 text-sm text-zinc-500">{data.partial_credit}</p>
      </header>

      <section aria-labelledby="grades">
        <h2 id="grades" className="text-lg font-semibold text-zinc-100">
          Grades
        </h2>
        <ul className="mt-3 flex flex-wrap gap-2 text-sm">
          {Object.entries(data.grades).map(([g, range]) => (
            <li key={g} className="rounded-lg border border-white/10 px-3 py-1.5 text-zinc-300">
              <span className="font-semibold text-zinc-100">{g}</span> {range}
            </li>
          ))}
        </ul>
      </section>

      {data.categories.map((cat) => {
        const checks = data.checks.filter((c) => c.category === cat.id);
        return (
          <section key={cat.id} aria-labelledby={`cat-${cat.id}`} className="surface p-6">
            <div className="flex items-baseline justify-between gap-4">
              <h2 id={`cat-${cat.id}`} className="text-lg font-semibold text-zinc-100">
                {cat.title}
              </h2>
              <span className="text-sm tabular-nums text-zinc-400">{cat.weight} points</span>
            </div>
            <table className="mt-4 w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-zinc-500">
                <tr>
                  <th className="py-2 font-medium">Check</th>
                  <th className="py-2 text-right font-medium">Points</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {checks.map((c) => (
                  <tr key={c.id}>
                    <td className="py-2.5 pr-4 align-top">
                      <span className="text-zinc-200">{c.title}</span>
                      {c.critical_if_missing && <span className="ml-2 rounded bg-alert-500/15 px-1.5 py-0.5 text-[10px] uppercase text-alert-400">critical</span>}
                      <p className="mt-0.5 text-xs text-zinc-500">{c.recommendation}</p>
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-zinc-300">{c.max_points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        );
      })}

      <section className="surface p-6 text-sm text-zinc-400">
        <h2 className="text-lg font-semibold text-zinc-100">Limits and honesty</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>Analyses read the default branch and the most recent 30 commits, issues and pull requests, not full history.</li>
          <li>A score measures what is visible to newcomers. It does not measure code quality or the project&apos;s importance.</li>
          <li>Only public repositories are analysed. Private repositories are refused and never stored.</li>
        </ul>
      </section>
    </article>
  );
}
