"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatCount, gradeTone, timeAgo } from "@/lib/format";
import type { Category, Check, Generated, Report, Severity } from "@/lib/types";
import { CopyButton } from "./CopyButton";

const TONE = {
  emerald: { text: "text-signal-400", stroke: "#34d399", bg: "bg-signal-500" },
  cyan: { text: "text-radar-300", stroke: "#67e8f9", bg: "bg-radar-500" },
  amber: { text: "text-caution-400", stroke: "#fbbf24", bg: "bg-caution-500" },
  rose: { text: "text-alert-400", stroke: "#fb7185", bg: "bg-alert-500" },
} as const;

export function ReportView({ report }: { report: Report }) {
  const tone = TONE[gradeTone(report.score)];
  return (
    <div className="space-y-8 animate-fade-up">
      <Header report={report} />
      {report.warnings.length > 0 && (
        <div className="surface border-caution-500/30 px-5 py-4 text-sm text-caution-400">
          <p className="font-medium">Some data could not be fetched:</p>
          <ul className="mt-1 list-disc pl-5 text-zinc-300">
            {report.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      <section aria-labelledby="score-heading" className="grid gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
        <div className="surface flex flex-col items-center justify-center p-8">
          <h2 id="score-heading" className="sr-only">
            Health score
          </h2>
          <ScoreRing score={report.score} stroke={tone.stroke} />
          <p className={`mt-4 text-3xl font-semibold ${tone.text}`}>Grade {report.grade}</p>
          <p className="mt-2 text-center text-sm text-zinc-400">{report.verdict}</p>
          <dl className="mt-6 grid w-full grid-cols-3 gap-2 text-center">
            <SummaryStat label="Critical" value={report.summary.critical} tone="text-alert-400" />
            <SummaryStat label="Warnings" value={report.summary.warning} tone="text-caution-400" />
            <SummaryStat label="Good" value={report.summary.good} tone="text-signal-400" />
          </dl>
          <Link href="/methodology" className="mt-6 text-xs text-zinc-500 underline-offset-4 hover:text-radar-300 hover:underline">
            How this score is calculated (methodology v{report.methodology_version})
          </Link>
        </div>
        <CategoryBars categories={report.categories} />
      </section>

      <Findings checks={report.checks} />
      <Activity report={report} />
      <Generators owner={report.repo.owner} name={report.repo.name} />
    </div>
  );
}

function Header({ report }: { report: Report }) {
  const r = report.repo;
  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <a href={r.url} target="_blank" rel="noreferrer" className="text-sm text-zinc-500 hover:text-radar-300">
          github.com/{r.owner}
        </a>
        <h1 className="mt-1 break-words text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">{r.name}</h1>
        {r.description && <p className="mt-2 max-w-2xl text-zinc-400">{r.description}</p>}
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-zinc-300">
          {r.language && <Chip>{r.language}</Chip>}
          {r.license && <Chip>{r.license}</Chip>}
          <Chip>★ {formatCount(r.stars)}</Chip>
          <Chip>⑂ {formatCount(r.forks)}</Chip>
          <Chip>Last push {timeAgo(r.pushed_at)}</Chip>
          {r.archived && <Chip tone="warn">Archived</Chip>}
        </div>
      </div>
      <ShareButton report={report} />
    </header>
  );
}

function Chip({ children, tone }: { children: React.ReactNode; tone?: "warn" }) {
  return (
    <span
      className={`rounded-full border px-3 py-1 ${
        tone === "warn" ? "border-caution-500/40 text-caution-400" : "border-white/10 bg-white/[0.03]"
      }`}
    >
      {children}
    </span>
  );
}

function SummaryStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-xl bg-white/[0.03] py-3">
      <dt className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</dt>
      <dd className={`mt-1 text-xl font-semibold ${tone}`}>{value}</dd>
    </div>
  );
}

export function ScoreRing({ score, stroke }: { score: number; stroke: string }) {
  const radius = 84;
  const circumference = 2 * Math.PI * radius;
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score]);
  const offset = circumference * (1 - shown / 100);
  return (
    <div className="relative h-52 w-52">
      <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90" role="img" aria-label={`Health score ${score} out of 100`}>
        <circle cx="100" cy="100" r={radius} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="14" />
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={stroke}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.1s cubic-bezier(.2,.8,.2,1)", filter: `drop-shadow(0 0 10px ${stroke}55)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-6xl font-semibold tabular-nums text-zinc-50">{score}</span>
        <span className="text-xs uppercase tracking-widest text-zinc-500">out of 100</span>
      </div>
    </div>
  );
}

function CategoryBars({ categories }: { categories: Category[] }) {
  return (
    <div className="surface p-6">
      <h2 className="text-lg font-semibold text-zinc-100">Category breakdown</h2>
      <p className="mt-1 text-sm text-zinc-500">Points earned per category. Weights sum to 100.</p>
      <ul className="mt-6 space-y-4">
        {categories.map((c) => {
          const pct = c.max_points ? Math.round((c.points / c.max_points) * 100) : 0;
          const tone = pct >= 80 ? "bg-signal-500" : pct >= 50 ? "bg-radar-500" : pct >= 25 ? "bg-caution-500" : "bg-alert-500";
          return (
            <li key={c.id}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-zinc-300">{c.title}</span>
                <span className="tabular-nums text-zinc-400">
                  {c.points}/{c.max_points}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/[0.06]" role="progressbar" aria-label={c.title} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
                <div className={`h-full rounded-full ${tone} transition-[width] duration-[1100ms] ease-out`} style={{ width: `${pct}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const SEVERITY_META: Record<Severity, { label: string; dot: string; heading: string }> = {
  critical: { label: "Critical", dot: "bg-alert-500", heading: "text-alert-400" },
  warning: { label: "Warning", dot: "bg-caution-500", heading: "text-caution-400" },
  good: { label: "Good", dot: "bg-signal-500", heading: "text-signal-400" },
};

function Findings({ checks }: { checks: Check[] }) {
  const groups: Record<Severity, Check[]> = { critical: [], warning: [], good: [] };
  for (const c of checks) groups[c.severity].push(c);
  return (
    <section aria-labelledby="findings-heading">
      <h2 id="findings-heading" className="text-lg font-semibold text-zinc-100">
        Findings
      </h2>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {(["critical", "warning", "good"] as Severity[]).map((sev) => (
          <div key={sev} className="surface flex flex-col p-4">
            <h3 className={`flex items-center gap-2 text-sm font-semibold ${SEVERITY_META[sev].heading}`}>
              <span className={`h-2 w-2 rounded-full ${SEVERITY_META[sev].dot}`} />
              {SEVERITY_META[sev].label} <span className="text-zinc-500">({groups[sev].length})</span>
            </h3>
            <ul className="mt-4 space-y-3">
              {groups[sev].length === 0 && <li className="text-sm text-zinc-500">Nothing here.</li>}
              {groups[sev].map((c) => (
                <li key={c.id} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-zinc-200">{c.title}</p>
                    <span className="shrink-0 text-xs tabular-nums text-zinc-500">
                      {c.points}/{c.max_points}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-400">{c.evidence}</p>
                  {c.recommendation && <p className="mt-2 text-xs text-radar-300">→ {c.recommendation}</p>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

function Activity({ report }: { report: Report }) {
  const s = report.stats;
  const max = Math.max(1, ...s.commit_activity.map((b) => b.count));
  return (
    <section aria-labelledby="activity-heading" className="grid gap-6 lg:grid-cols-2">
      <div className="surface p-6 lg:col-span-2">
        <h2 id="activity-heading" className="text-lg font-semibold text-zinc-100">
          Commit activity
        </h2>
        <p className="mt-1 text-sm text-zinc-500">Commits per week, from the most recent commits sampled from GitHub.</p>
        <div className="mt-6 flex h-36 items-end gap-2" role="img" aria-label="Weekly commit counts">
          {s.commit_activity.map((b) => (
            <div key={b.week} className="group flex h-full flex-1 flex-col justify-end">
              <div
                className="rounded-t-md bg-gradient-to-t from-radar-600/70 to-signal-400/90 transition-all duration-700 group-hover:brightness-125"
                style={{ height: `${Math.max(b.count ? 6 : 2, (b.count / max) * 100)}%`, opacity: b.count ? 1 : 0.25 }}
                title={`${b.count} commit(s) week of ${b.week}`}
              />
            </div>
          ))}
        </div>
        <div className="mt-2 flex justify-between text-[11px] text-zinc-600">
          <span>12 weeks ago</span>
          <span>this week</span>
        </div>
      </div>

      <ListCard title="Recent commits" empty="No commits returned by GitHub." count={s.recent_commits.length}>
        {s.recent_commits.map((c) => (
          <ListRow key={c.sha + c.date} href={c.url} title={c.message || "(no message)"} meta={`${c.sha} · ${c.author} · ${timeAgo(c.date)}`} />
        ))}
      </ListCard>

      <ListCard title="Recent issues" empty="No issues." count={s.recent_issues.length}>
        {s.recent_issues.map((i) => (
          <ListRow key={i.number} href={i.url} title={`#${i.number} ${i.title}`} meta={`${i.state} · ${i.comments} comments · ${timeAgo(i.created_at)}`} />
        ))}
      </ListCard>

      <ListCard title="Recent pull requests" empty="No pull requests." count={s.recent_pulls.length}>
        {s.recent_pulls.map((p) => (
          <ListRow key={p.number} href={p.url} title={`#${p.number} ${p.title}`} meta={`${p.merged ? "merged" : p.state} · ${timeAgo(p.created_at)}`} />
        ))}
      </ListCard>

      <div className="surface p-6">
        <h3 className="text-sm font-semibold text-zinc-200">Top contributors</h3>
        {s.contributors.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No contributor data.</p>
        ) : (
          <ul className="mt-4 grid grid-cols-2 gap-3">
            {s.contributors.map((c) => (
              <li key={c.login} className="flex items-center gap-3 rounded-xl bg-white/[0.03] p-2">
                {c.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.avatar_url} alt="" width={32} height={32} className="h-8 w-8 rounded-full" loading="lazy" />
                ) : (
                  <span className="h-8 w-8 rounded-full bg-white/10" />
                )}
                <div className="min-w-0">
                  <a href={c.url ?? undefined} target="_blank" rel="noreferrer" className="block truncate text-sm text-zinc-200 hover:text-radar-300">
                    {c.login}
                  </a>
                  <span className="text-xs text-zinc-500">{formatCount(c.contributions)} commits</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="surface p-6 lg:col-span-2">
        <h3 className="text-sm font-semibold text-zinc-200">Latest workflow runs</h3>
        {s.workflow_runs.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No workflow runs returned.</p>
        ) : (
          <ul className="mt-4 flex flex-wrap gap-2">
            {s.workflow_runs.map((r, idx) => {
              const ok = r.conclusion === "success";
              const label = r.conclusion ?? r.status;
              return (
                <li key={`${r.name}-${idx}`}>
                  <a
                    href={r.url ?? undefined}
                    target="_blank"
                    rel="noreferrer"
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${
                      ok ? "border-signal-500/40 text-signal-400" : "border-caution-500/40 text-caution-400"
                    }`}
                  >
                    {r.name} · {label} · {timeAgo(r.created_at)}
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

function ListCard({
  title,
  empty,
  count,
  children,
}: {
  title: string;
  empty: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="surface p-6">
      <h3 className="text-sm font-semibold text-zinc-200">{title}</h3>
      {count > 0 ? (
        <ul className="mt-4 divide-y divide-white/[0.05]">{children}</ul>
      ) : (
        <p className="mt-3 text-sm text-zinc-500">{empty}</p>
      )}
    </div>
  );
}

function ListRow({ href, title, meta }: { href: string | null; title: string; meta: string }) {
  return (
    <li className="py-3">
      <a href={href ?? undefined} target="_blank" rel="noreferrer" className="block truncate text-sm text-zinc-200 hover:text-radar-300">
        {title}
      </a>
      <p className="mt-0.5 truncate text-xs text-zinc-500">{meta}</p>
    </li>
  );
}

const GENERATOR_KINDS = [
  { kind: "readme", label: "README.md" },
  { kind: "contributing", label: "CONTRIBUTING.md" },
  { kind: "issue-templates", label: "Issue templates" },
  { kind: "pr-template", label: "PR template" },
] as const;

function Generators({ owner, name }: { owner: string; name: string }) {
  const [active, setActive] = useState<string | null>(null);
  const [data, setData] = useState<Generated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(kind: string) {
    setActive(kind);
    setLoading(true);
    setError(null);
    try {
      setData(await api.generate(owner, name, kind));
    } catch (err) {
      setData(null);
      setError(err instanceof ApiError ? err.message : "Could not generate this file.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-labelledby="gen-heading" className="surface p-6">
      <h2 id="gen-heading" className="text-lg font-semibold text-zinc-100">
        Generate starter files
      </h2>
      <p className="mt-1 text-sm text-zinc-500">
        Drafts built from what RepoRadar detected (install and test commands, license). Fill in the TODO markers before committing.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {GENERATOR_KINDS.map((g) => (
          <button
            key={g.kind}
            type="button"
            onClick={() => load(g.kind)}
            aria-pressed={active === g.kind}
            className={`rounded-xl border px-4 py-2 text-sm transition ${
              active === g.kind ? "border-radar-400/60 bg-radar-500/10 text-radar-300" : "border-white/10 text-zinc-300 hover:border-white/25"
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>
      <div className="mt-4" aria-live="polite">
        {loading && <div className="skeleton h-40 w-full" />}
        {error && <p className="text-sm text-alert-400">{error}</p>}
        {data && !loading && (
          <div className="space-y-4">
            {data.files.map((f) => (
              <div key={f.path} className="overflow-hidden rounded-xl border border-white/10 bg-black/40">
                <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
                  <code className="text-xs text-zinc-400">{f.path}</code>
                  <CopyButton text={f.content} />
                </div>
                <pre className="max-h-96 overflow-auto p-4 text-xs leading-relaxed text-zinc-300">{f.content}</pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function ShareButton({ report }: { report: Report }) {
  const [state, setState] = useState<{ status: "idle" | "working" | "done" | "error"; url?: string; message?: string }>({
    status: "idle",
  });

  async function share() {
    setState({ status: "working" });
    try {
      const { path } = await api.createShare(report.repo.full_name);
      const url = `${window.location.origin}${path}`;
      setState({ status: "done", url });
      try {
        await navigator.clipboard.writeText(url);
      } catch {
        // Clipboard may be unavailable; the link is still shown below.
      }
    } catch (err) {
      setState({ status: "error", message: err instanceof ApiError ? err.message : "Could not create a share link." });
    }
  }

  return (
    <div className="w-full md:w-auto md:text-right">
      <button
        type="button"
        onClick={share}
        disabled={state.status === "working"}
        className="w-full rounded-xl border border-white/15 bg-white/[0.04] px-4 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-radar-400/50 hover:text-radar-300 disabled:opacity-60 md:w-auto"
      >
        {state.status === "working" ? "Creating link…" : "Create shareable report"}
      </button>
      {state.status === "done" && state.url && (
        <p className="mt-2 break-all text-xs text-signal-400">
          Link copied: <a href={state.url} className="underline">{state.url}</a>
        </p>
      )}
      {state.status === "error" && <p className="mt-2 text-xs text-alert-400">{state.message}</p>}
      <p className="mt-2 hidden text-[11px] text-zinc-600 md:block">
        <Link href="/contribute" className="hover:text-radar-300">Find good first issues →</Link>
      </p>
    </div>
  );
}
