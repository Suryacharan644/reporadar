"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { quickRepoCheck } from "@/lib/format";
import type { Validation } from "@/lib/types";

type State =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "valid"; info: Validation }
  | { kind: "invalid"; message: string };

const EXAMPLES = ["fastapi/fastapi", "psf/requests", "tiangolo/typer", "vercel/next.js"];

export function RepoInput({ initial = "" }: { initial?: string }) {
  const router = useRouter();
  const [value, setValue] = useState(initial);
  const [state, setState] = useState<State>({ kind: "idle" });

  // Instant validation: debounce, then ask the backend (which checks GitHub).
  useEffect(() => {
    const text = value.trim();
    if (!text) {
      setState({ kind: "idle" });
      return;
    }
    const offline = quickRepoCheck(text);
    if (offline) {
      setState({ kind: "invalid", message: offline });
      return;
    }
    const controller = new AbortController();
    setState({ kind: "checking" });
    const timer = setTimeout(async () => {
      try {
        const info = await api.validate(text, controller.signal);
        if (info.private) {
          setState({ kind: "invalid", message: "This repository is private. RepoRadar only analyses public repositories." });
        } else {
          setState({ kind: "valid", info });
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const message = err instanceof ApiError ? err.message : "Could not validate this repository.";
        setState({ kind: "invalid", message });
      }
    }, 450);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (state.kind !== "valid") return;
    router.push(`/r/${state.info.full_name}`);
  }

  const ring =
    state.kind === "valid"
      ? "border-signal-500/50 focus-within:ring-signal-500/30"
      : state.kind === "invalid"
        ? "border-alert-500/50 focus-within:ring-alert-500/30"
        : "border-white/10 focus-within:ring-radar-500/30";

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={submit} className="group">
        <label htmlFor="repo" className="sr-only">
          GitHub repository URL or owner/repo
        </label>
        <div className={`flex items-center gap-2 rounded-2xl border bg-white/[0.04] p-2 pl-4 ring-4 ring-transparent transition ${ring}`}>
          <span aria-hidden className="text-zinc-500">github.com/</span>
          <input
            id="repo"
            name="repo"
            autoComplete="off"
            spellCheck={false}
            placeholder="owner/repo"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-invalid={state.kind === "invalid"}
            aria-describedby="repo-status"
            className="min-w-0 flex-1 bg-transparent py-2 text-base text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={state.kind !== "valid"}
            className="rounded-xl bg-gradient-to-r from-radar-500 to-signal-500 px-5 py-2.5 text-sm font-semibold text-zinc-950 shadow-lg shadow-radar-500/20 transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Analyse
          </button>
        </div>
      </form>

      <div id="repo-status" role="status" aria-live="polite" className="mt-3 min-h-[3.5rem] text-sm">
        {state.kind === "checking" && (
          <p className="flex items-center gap-2 text-zinc-400">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-radar-400 border-t-transparent" />
            Checking repository on GitHub…
          </p>
        )}
        {state.kind === "invalid" && <p className="text-alert-400">{state.message}</p>}
        {state.kind === "valid" && (
          <div className="surface flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3">
            <span className="font-medium text-zinc-100">{state.info.full_name}</span>
            <span className="text-zinc-400">★ {state.info.stars.toLocaleString("en")}</span>
            {state.info.language && <span className="text-zinc-400">{state.info.language}</span>}
            {state.info.archived && <span className="text-caution-400">Archived</span>}
            {state.info.description && <span className="w-full truncate text-zinc-500">{state.info.description}</span>}
          </div>
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-zinc-500">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setValue(ex)}
            className="rounded-full border border-white/10 px-3 py-1 text-zinc-300 transition hover:border-radar-400/50 hover:text-radar-300"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
