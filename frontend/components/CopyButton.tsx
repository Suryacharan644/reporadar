"use client";

import { useState } from "react";

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-md border border-white/10 px-2.5 py-1 text-xs text-zinc-300 transition hover:border-radar-400/50 hover:text-radar-300"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
