import type { Metadata } from "next";
import { ContributeFinder } from "@/components/ContributeFinder";

export const metadata: Metadata = { title: "Find good first issues" };

export default function ContributePage() {
  return (
    <div className="space-y-8">
      <header className="max-w-2xl">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-radar-300">Open source contribution</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-50 md:text-4xl">Find your first contribution</h1>
        <p className="mt-3 text-zinc-400">
          Open issues that maintainers have labelled as beginner-friendly, pulled live from GitHub across public repositories.
        </p>
      </header>
      <ContributeFinder />
    </div>
  );
}
