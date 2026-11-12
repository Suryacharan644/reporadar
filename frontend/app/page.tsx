import Link from "next/link";
import { RepoInput } from "@/components/RepoInput";

const FEATURES = [
  {
    title: "Ten evidence-based checks",
    body: "README, license, CONTRIBUTING, templates, CI, tests, dependencies and activity, each scored with the evidence that produced it.",
  },
  {
    title: "Critical, warning, good",
    body: "Every finding is ranked so you know what blocks newcomers first, with a concrete fix for each problem.",
  },
  {
    title: "Starter files, generated",
    body: "Draft README, CONTRIBUTING, issue and PR templates built from your repository's real install and test commands.",
  },
  {
    title: "Shareable reports",
    body: "Send a read-only link to maintainers or your team. Only public data is stored.",
  },
  {
    title: "Runs on every pull request",
    body: "A GitHub Action posts an updated health comment on PRs and can fail the build below a score you choose.",
  },
  {
    title: "Find good first issues",
    body: "Browse open, beginner-labelled issues across GitHub to make your first contribution to a healthy project.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-20">
      <section className="relative pt-6 md:pt-10">
        <div aria-hidden className="pointer-events-none absolute -top-10 left-1/2 h-72 w-[38rem] -translate-x-1/2 rounded-full bg-radar-500/10 blur-3xl animate-drift" />
        <p className="animate-fade-up text-sm font-medium uppercase tracking-[0.2em] text-radar-300">Repository health</p>
        <h1 className="animate-fade-up mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-zinc-50 md:text-6xl">
          Find out why developers <span className="gradient-text">leave your repository</span> without contributing.
        </h1>
        <p className="animate-fade-up mt-6 max-w-2xl text-lg leading-relaxed text-zinc-400">
          Paste any public GitHub repository and get a transparent 0–100 health score, the problems that stop newcomers, and
          the exact changes that fix them.
        </p>
        <div className="animate-fade-up mt-10">
          <RepoInput />
        </div>
      </section>

      <section aria-labelledby="features-heading">
        <h2 id="features-heading" className="sr-only">
          Features
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <article key={f.title} className="surface p-6 transition hover:border-white/20">
              <h3 className="text-base font-semibold text-zinc-100">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-zinc-400">{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="surface flex flex-col items-start justify-between gap-6 p-8 md:flex-row md:items-center">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100">Want to see how the score works?</h2>
          <p className="mt-1 text-sm text-zinc-400">Every check, its points and its recommendation are published and versioned.</p>
        </div>
        <Link href="/methodology" className="rounded-xl border border-white/15 px-5 py-2.5 text-sm font-medium text-zinc-100 transition hover:border-radar-400/50 hover:text-radar-300">
          Read the methodology
        </Link>
      </section>
    </div>
  );
}
